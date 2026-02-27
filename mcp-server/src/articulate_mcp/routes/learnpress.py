"""Endpoints for LearnPress detection, management, and LMS data proxying."""

from __future__ import annotations

import asyncio
import logging
import json
import tempfile
from pathlib import Path
from typing import Optional

import re
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse

from articulate_mcp.user_manager import UserManager
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.graphql.client import get_graphql_client, GraphQLError

logger = logging.getLogger(__name__)


async def _auth_and_connection(request: Request) -> tuple[Optional[dict], Optional[dict], Optional[JSONResponse]]:
    """Authenticate request and get WP connection. Returns (user, connection, error_response)."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return None, None, JSONResponse({"error": "Session required"}, status_code=401)

    user = await UserManager.get_user_from_session(session_id)
    if not user:
        return None, None, JSONResponse({"error": "Invalid session"}, status_code=401)

    connection_id = int(request.path_params.get("id"))
    connection = await connection_manager.get_connection(connection_id, user["id"])
    if not connection:
        return user, None, JSONResponse({"error": "Connection not found"}, status_code=404)

    return user, connection, None


def _lp_client(connection: dict, namespace: str = "learnpress/v1") -> httpx.AsyncClient:
    """Create httpx client for LearnPress REST API."""
    wp_url = connection["wp_url"].rstrip("/")
    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/{namespace}",
        auth=(connection["wp_user"], connection["wp_app_password"]),
        timeout=30.0,
    )


async def check_learnpress_endpoint(request):
    """Check whether LearnPress is installed on a connected WordPress site.

    Tries GraphQL introspection first, then falls back to REST endpoint checks.
    """
    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))

        # Try GraphQL introspection first
        try:
            client = await get_graphql_client(connection_id, user["id"])
            introspection = "query Introspect { __schema { types { name } } }"
            result = await client.execute(introspection)
            types = [t.get("name", "") for t in result.get("__schema", {}).get("types", [])]
            matched = [t for t in types if "course" in t.lower() or "learnpress" in t.lower()]
            if matched:
                return JSONResponse({"installed": True, "method": "graphql", "matches": matched})
        except Exception as e:
            # GraphQL may not expose learnpress types or introspection may be disabled
            logger.debug("GraphQL introspection failed or plugin not present: %s", e)

        # Fallback to REST endpoint checks
        connection = await connection_manager.get_connection(connection_id, user["id"])
        if not connection:
            return JSONResponse({"error": "Connection not found"}, status_code=404)

        wp_url = connection["wp_url"].rstrip("/")
        wp_user = connection["wp_user"]
        wp_pass = connection.get("wp_app_password")

        async with httpx.AsyncClient(base_url=wp_url + "/wp-json", auth=(wp_user, wp_pass), timeout=10.0) as client:
            endpoints = [
                "learnpress/v1",
                "learnpress/v1/courses",
                "lp/v1",
                "lp/v1/courses",
                "learnpress/v1/courses?per_page=1",
            ]

            for ep in endpoints:
                try:
                    url = ep if ep.startswith("/") else f"/{ep}"
                    resp = await client.get(url)
                    # If authorized and endpoint exists, assume plugin present
                    if resp.status_code == 200:
                        sample = None
                        try:
                            sample = resp.json()
                        except Exception:
                            sample = None
                        return JSONResponse({
                            "installed": True,
                            "method": "rest",
                            "endpoint": ep,
                            "status": resp.status_code,
                            "sample": sample,
                        })
                    # If unauthorized, report that credential lacks permissions
                    if resp.status_code in (401, 403):
                        return JSONResponse({"installed": False, "error": "unauthorized", "status": resp.status_code})
                except httpx.HTTPError as e:
                    logger.debug("REST check failed for %s: %s", ep, e)

        # None of the checks detected LearnPress
        return JSONResponse({"installed": False})

    except Exception as e:
        logger.error("Check LearnPress error: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to check LearnPress", "details": str(e)}, status_code=500)


async def install_learnpress_endpoint(request):
    """Install LearnPress on a connected WordPress site.

    Attempt order:
      1. GraphQL mutation (if exposed by the site)
      2. REST endpoint (if the site exposes plugin management)
      3. SSH-based setup script (requires ssh credentials in request)
    """
    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        data = await request.json()
        plugin_slug = data.get("plugin_slug", "learnpress")
        # Sanitize plugin_slug: only allow lowercase letters, numbers, hyphen and underscore
        if not isinstance(plugin_slug, str) or not re.match(r'^[a-z0-9_-]+$', plugin_slug):
            return JSONResponse({"error": "invalid_plugin_slug", "details": "plugin_slug must match ^[a-z0-9_-]+$"}, status_code=400)

        # 1) Try GraphQL mutation
        try:
            client = await get_graphql_client(connection_id, user["id"])
            mutation = """
            mutation InstallPlugin($slug: String!) {
              installPlugin(slug: $slug) {
                success
                message
              }
            }
            """
            result = await client.mutate(mutation, {"slug": plugin_slug})

            # If the GraphQL endpoint returned something, consider it success
            if result and ("installPlugin" in result or any(k.lower().startswith("install") for k in result.keys())):
                return JSONResponse({"success": True, "method": "graphql", "result": result})
        except Exception as e:
            logger.debug("GraphQL install attempt failed: %s", e)

        # 2) Try REST endpoint (best-effort)
        connection = await connection_manager.get_connection(connection_id, user["id"])
        if not connection:
            return JSONResponse({"error": "Connection not found"}, status_code=404)

        wp_url = connection["wp_url"].rstrip("/")
        wp_user = connection["wp_user"]
        wp_pass = connection.get("wp_app_password")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(f"{wp_url}/wp-json/wp/v2/plugins", json={"slug": plugin_slug}, auth=(wp_user, wp_pass))
                if resp.status_code in (200, 201, 202, 204):
                    try:
                        body = resp.json()
                    except Exception:
                        body = None
                    return JSONResponse({"success": True, "method": "rest", "status": resp.status_code, "body": body})
                if resp.status_code in (401, 403):
                    return JSONResponse({"error": "unauthorized", "status": resp.status_code}, status_code=403)
            except httpx.HTTPError as e:
                logger.debug("REST install attempt failed: %s", e)

        # 3) Fallback: run remote setup script via SSH if credentials were provided in the request
        ssh_host = data.get("ssh_host") or data.get("host")
        if ssh_host:
            ssh_user = data.get("ssh_user") or data.get("user")
            port = int(data.get("ssh_port", 22))
            ssh_key = data.get("ssh_key")
            ssh_password = data.get("ssh_password")
            wp_path = data.get("wp_path")

            # Find the setup script
            script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "setup-remote-wordpress.py"
            if not script_path.exists():
                return JSONResponse({"error": "Setup script not found"}, status_code=500)

            cmd = ["python3", str(script_path), "--host", ssh_host, "--user", ssh_user, "--port", str(port), "--plugins", plugin_slug]
            if wp_path:
                cmd.extend(["--wp-path", wp_path])

            key_file = None
            try:
                if ssh_key:
                    key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
                    key_file.write(ssh_key)
                    key_file.close()
                    Path(key_file.name).chmod(0o600)
                    cmd.extend(["--key", key_file.name])
                else:
                    cmd.extend(["--password", ssh_password])

                logger.info("Running remote plugin install via SSH for %s", ssh_host)
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if key_file:
                    try:
                        Path(key_file.name).unlink()
                    except Exception:
                        pass

                output = stdout.decode() if stdout else ""
                err = stderr.decode() if stderr else ""

                if process.returncode != 0:
                    logger.error("SSH install failed: %s", err)
                    return JSONResponse({"error": "SSH install failed", "details": err}, status_code=500)

                return JSONResponse({"success": True, "method": "ssh", "output": output})
            except Exception as e:
                logger.error("SSH install exception: %s", e, exc_info=True)
                return JSONResponse({"error": "SSH install failed", "details": str(e)}, status_code=500)

        # If all attempts failed
        return JSONResponse({"error": "Failed to install plugin via GraphQL and REST. Provide SSH credentials to attempt remote install."}, status_code=500)

    except Exception as e:
        logger.error("Install LearnPress error: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to install LearnPress", "details": str(e)}, status_code=500)


# ── Phase 3: REST proxy routes for LearnPress data ──────────────────


async def lp_list_courses_endpoint(request: Request):
    """List LearnPress courses for a connection."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    try:
        params = dict(request.query_params)
        async with _lp_client(connection) as client:
            resp = await client.get("/courses", params=params)
            if resp.status_code == 404:
                return JSONResponse({"courses": [], "learnpress_installed": False})
            resp.raise_for_status()
            return JSONResponse({"courses": resp.json(), "learnpress_installed": True})
    except Exception as e:
        logger.error("List LP courses error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_get_course_endpoint(request: Request):
    """Get a single LearnPress course with curriculum."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    course_id = request.path_params.get("course_id")
    try:
        async with _lp_client(connection) as client:
            resp = await client.get(f"/courses/{course_id}")
            if resp.status_code == 404:
                return JSONResponse({"error": "Course not found"}, status_code=404)
            resp.raise_for_status()
            return JSONResponse(resp.json())
    except Exception as e:
        logger.error("Get LP course error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_enroll_endpoint(request: Request):
    """Enroll the authenticated user in a course."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    course_id = request.path_params.get("course_id")
    try:
        async with _lp_client(connection) as client:
            resp = await client.post("/courses/enroll", json={"id": int(course_id)})
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if resp.status_code >= 400:
                return JSONResponse({"error": data.get("message", "Enrollment failed")}, status_code=resp.status_code)
            return JSONResponse({"success": True, "data": data})
    except Exception as e:
        logger.error("LP enroll error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_course_students_endpoint(request: Request):
    """List students enrolled in a course (via admin API)."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    course_id = request.path_params.get("course_id")
    try:
        # Use lp/v1 admin namespace for student listing
        async with _lp_client(connection, namespace="lp/v1") as client:
            resp = await client.get("/admin/users", params={
                "course_id": course_id,
                **dict(request.query_params),
            })
            if resp.status_code == 404:
                return JSONResponse({"students": []})
            resp.raise_for_status()
            return JSONResponse({"students": resp.json()})
    except Exception as e:
        logger.error("LP course students error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_list_quizzes_endpoint(request: Request):
    """List LearnPress quizzes for a connection."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    try:
        params = dict(request.query_params)
        async with _lp_client(connection) as client:
            resp = await client.get("/quiz", params=params)
            if resp.status_code == 404:
                return JSONResponse({"quizzes": []})
            resp.raise_for_status()
            return JSONResponse({"quizzes": resp.json()})
    except Exception as e:
        logger.error("List LP quizzes error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_get_quiz_endpoint(request: Request):
    """Get a single LearnPress quiz with questions."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    quiz_id = request.path_params.get("quiz_id")
    try:
        async with _lp_client(connection) as client:
            resp = await client.get(f"/quiz/{quiz_id}")
            if resp.status_code == 404:
                return JSONResponse({"error": "Quiz not found"}, status_code=404)
            resp.raise_for_status()
            return JSONResponse(resp.json())
    except Exception as e:
        logger.error("Get LP quiz error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_orders_endpoint(request: Request):
    """List LearnPress orders (admin)."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    try:
        params = dict(request.query_params)
        async with _lp_client(connection, namespace="lp/v1") as client:
            resp = await client.get("/admin/orders", params=params)
            if resp.status_code == 404:
                return JSONResponse({"orders": []})
            resp.raise_for_status()
            return JSONResponse({"orders": resp.json()})
    except Exception as e:
        logger.error("LP orders error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def lp_student_progress_endpoint(request: Request):
    """Get student progress/statistics for the authenticated user."""
    user, connection, err = await _auth_and_connection(request)
    if err:
        return err

    try:
        async with _lp_client(connection, namespace="lp/v1") as client:
            resp = await client.get("/profile/student/statistic")
            if resp.status_code == 404:
                return JSONResponse({"progress": {}})
            resp.raise_for_status()
            return JSONResponse({"progress": resp.json()})
    except Exception as e:
        logger.error("LP student progress error: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
