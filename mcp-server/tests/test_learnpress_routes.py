"""Tests for LearnPress Phase 3 REST proxy route handlers."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from articulate_mcp.routes import learnpress as lp_route


class FakeRequest:
    """Minimal request-like object for route handler testing."""
    def __init__(self, headers=None, path_params=None, query_params=None, json_data=None):
        self.headers = headers or {}
        self.path_params = path_params or {}
        self.query_params = query_params or {}
        self._json = json_data

    async def json(self):
        return self._json


def _authed_request(path_params=None, query_params=None, json_data=None):
    """Create a request with valid session header."""
    return FakeRequest(
        headers={"X-Session-ID": "valid-session"},
        path_params=path_params or {"id": "1"},
        query_params=query_params or {},
        json_data=json_data,
    )


def _mock_httpx_response(status_code=200, json_data=None, headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = headers or {"content-type": "application/json"}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=resp
        )
    return resp


class FakeUserManager:
    @staticmethod
    async def get_user_from_session(session_id):
        if session_id == "valid-session":
            return {"id": 123}
        return None


class FakeConnectionManager:
    async def get_connection(self, connection_id, user_id):
        return {
            "wp_url": "http://wordpress:80",
            "wp_user": "admin",
            "wp_app_password": "app-pass-123",
        }


class FakeConnectionManagerNotFound:
    async def get_connection(self, connection_id, user_id):
        return None


# ── _auth_and_connection tests ────────────────────────────────────


class TestAuthAndConnection:

    @pytest.mark.asyncio
    async def test_missing_session(self):
        req = FakeRequest(headers={}, path_params={"id": "1"})
        user, conn, err = await lp_route._auth_and_connection(req)
        assert user is None
        assert err is not None
        assert err.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_session(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        req = FakeRequest(headers={"X-Session-ID": "bad"}, path_params={"id": "1"})
        user, conn, err = await lp_route._auth_and_connection(req)
        assert user is None
        assert err.status_code == 401

    @pytest.mark.asyncio
    async def test_connection_not_found(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManagerNotFound())
        req = _authed_request()
        user, conn, err = await lp_route._auth_and_connection(req)
        assert user is not None
        assert conn is None
        assert err.status_code == 404

    @pytest.mark.asyncio
    async def test_successful_auth(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())
        req = _authed_request()
        user, conn, err = await lp_route._auth_and_connection(req)
        assert user == {"id": 123}
        assert conn is not None
        assert conn["wp_url"] == "http://wordpress:80"
        assert err is None


# ── _lp_client tests ─────────────────────────────────────────────


class TestLpClient:

    def test_creates_client_with_auth(self):
        conn = {
            "wp_url": "http://wordpress:80",
            "wp_user": "admin",
            "wp_app_password": "secret",
        }
        client = lp_route._lp_client(conn)
        # httpx normalises port 80 away and adds trailing slash
        assert "wp-json/learnpress/v1" in str(client.base_url)

    def test_creates_client_custom_namespace(self):
        conn = {
            "wp_url": "http://wordpress:80",
            "wp_user": "admin",
            "wp_app_password": "secret",
        }
        client = lp_route._lp_client(conn, namespace="lp/v1")
        assert "wp-json/lp/v1" in str(client.base_url)

    def test_no_auth_when_credentials_missing(self):
        conn = {
            "wp_url": "http://wordpress:80",
            "wp_user": None,
            "wp_app_password": None,
        }
        client = lp_route._lp_client(conn)
        assert client._auth is None


# ── error_response tests ─────────────────────────────────────────


class TestErrorResponse:

    def test_basic_error(self):
        resp = lp_route.error_response("test_error", "Something went wrong", 400)
        assert resp.status_code == 400
        body = json.loads(resp.body.decode())
        assert body["error"] == "test_error"
        assert body["error_info"]["message"] == "Something went wrong"

    def test_error_with_details(self):
        resp = lp_route.error_response("fail", "Failed", 500, details={"key": "val"})
        body = json.loads(resp.body.decode())
        assert body["error_info"]["details"] == {"key": "val"}


# ── Proxy endpoint tests ─────────────────────────────────────────


class TestLpListCoursesEndpoint:

    @pytest.mark.asyncio
    async def test_returns_courses(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        courses_data = [
            {"id": 1, "title": {"rendered": "Python 101"}, "status": "publish"},
            {"id": 2, "title": {"rendered": "JS Basics"}, "status": "draft"},
        ]
        mock_resp = _mock_httpx_response(200, courses_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_list_courses_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["learnpress_installed"] is True
        assert len(body["courses"]) == 2

    @pytest.mark.asyncio
    async def test_404_means_not_installed(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(404)
        mock_resp.raise_for_status = MagicMock()  # don't raise for 404 since code checks it

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_list_courses_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["learnpress_installed"] is False
        assert body["courses"] == []

    @pytest.mark.asyncio
    async def test_auth_failure_returns_error(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        req = FakeRequest(headers={}, path_params={"id": "1"})
        resp = await lp_route.lp_list_courses_endpoint(req)
        assert resp.status_code == 401


class TestLpGetCourseEndpoint:

    @pytest.mark.asyncio
    async def test_returns_course(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        course_data = {"id": 1, "title": {"rendered": "Python 101"}}
        mock_resp = _mock_httpx_response(200, course_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request(path_params={"id": "1", "course_id": "42"})
        resp = await lp_route.lp_get_course_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["id"] == 1

    @pytest.mark.asyncio
    async def test_course_not_found(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(404)
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request(path_params={"id": "1", "course_id": "999"})
        resp = await lp_route.lp_get_course_endpoint(req)
        assert resp.status_code == 404


class TestLpEnrollEndpoint:

    @pytest.mark.asyncio
    async def test_successful_enroll(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(200, {"enrolled": True})
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request(path_params={"id": "1", "course_id": "10"})
        resp = await lp_route.lp_enroll_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_enroll_fails(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(403, {"message": "Not allowed"})
        mock_resp.raise_for_status = MagicMock()  # don't raise, code checks status
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request(path_params={"id": "1", "course_id": "10"})
        resp = await lp_route.lp_enroll_endpoint(req)
        assert resp.status_code == 403


class TestLpListQuizzesEndpoint:

    @pytest.mark.asyncio
    async def test_returns_quizzes(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        quiz_data = [{"id": 1, "title": "Quiz 1"}]
        mock_resp = _mock_httpx_response(200, quiz_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_list_quizzes_endpoint(req)
        body = json.loads(resp.body.decode())
        assert len(body["quizzes"]) == 1

    @pytest.mark.asyncio
    async def test_empty_quizzes_on_404(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(404)
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_list_quizzes_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["quizzes"] == []


class TestLpGetQuizEndpoint:

    @pytest.mark.asyncio
    async def test_returns_quiz(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        quiz = {"id": 5, "title": "Final Exam", "questions": []}
        mock_resp = _mock_httpx_response(200, quiz)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request(path_params={"id": "1", "quiz_id": "5"})
        resp = await lp_route.lp_get_quiz_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["id"] == 5


class TestLpOrdersEndpoint:

    @pytest.mark.asyncio
    async def test_returns_orders(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        orders = [{"id": 100, "status": "completed"}]
        mock_resp = _mock_httpx_response(200, orders)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_orders_endpoint(req)
        body = json.loads(resp.body.decode())
        assert len(body["orders"]) == 1


class TestLpStudentProgressEndpoint:

    @pytest.mark.asyncio
    async def test_returns_progress(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        progress = {"courses_enrolled": 3, "courses_completed": 1}
        mock_resp = _mock_httpx_response(200, progress)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_student_progress_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["progress"]["courses_enrolled"] == 3

    @pytest.mark.asyncio
    async def test_empty_progress_on_404(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        mock_resp = _mock_httpx_response(404)
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, **kw: mock_client)

        req = _authed_request()
        resp = await lp_route.lp_student_progress_endpoint(req)
        body = json.loads(resp.body.decode())
        assert body["progress"] == {}


class TestLpCourseStudentsEndpoint:

    @pytest.mark.asyncio
    async def test_returns_students(self, monkeypatch):
        monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
        monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

        students = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        mock_resp = _mock_httpx_response(200, students)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr(lp_route, "_lp_client", lambda conn, namespace="lp/v1": mock_client)

        req = _authed_request(path_params={"id": "1", "course_id": "42"})
        resp = await lp_route.lp_course_students_endpoint(req)
        body = json.loads(resp.body.decode())
        assert len(body["students"]) == 2
