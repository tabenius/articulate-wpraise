"""Endpoints for LearnPress detection, management, and LMS data proxying."""

from __future__ import annotations

import asyncio
import logging
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import re
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from articulate_mcp.user_manager import UserManager
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.graphql.client import get_graphql_client, GraphQLError

logger = logging.getLogger(__name__)


def _get_correlation_id(request) -> str:
    """Get or generate a correlation ID for this request."""
    if hasattr(request, "state") and hasattr(request.state, "correlation_id"):
        return request.state.correlation_id
    return uuid.uuid4().hex[:12]

async def run_subprocess_exec(*args, **kwargs):
    """Wrapper around asyncio.create_subprocess_exec to allow monkeypatching in tests."""
    return await asyncio.create_subprocess_exec(*args, **kwargs)


def error_response(code: str, message: str, status_code: int = 400, details: Optional[object] = None) -> JSONResponse:
    """Return a structured error response while preserving a top-level error code for compatibility."""
    payload = {"error": code, "error_info": {"code": code, "message": message}}
    if details is not None:
        payload["error_info"]["details"] = details
    return JSONResponse(payload, status_code=status_code)


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
    auth_param = (connection.get("wp_user"), connection.get("wp_app_password")) if connection.get("wp_user") and connection.get("wp_app_password") else None
    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/{namespace}",
        auth=auth_param,
        timeout=30.0,
    )


async def check_learnpress_endpoint(request):
    """Check whether LearnPress is installed on a connected WordPress site.

    Tries GraphQL introspection first, then falls back to REST endpoint checks.
    """
    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return error_response("session_required", "Session required", status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return error_response("invalid_session", "Invalid session", status_code=401)

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
            return error_response("connection_not_found", "Connection not found", status_code=404)

        wp_url = connection["wp_url"].rstrip("/")
        wp_user = connection["wp_user"]
        wp_pass = connection.get("wp_app_password")

        auth_param = (wp_user, wp_pass) if wp_user and wp_pass else None
        async with httpx.AsyncClient(base_url=wp_url + "/wp-json", auth=auth_param, timeout=10.0) as client:
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
        return error_response("check_error", "Failed to check LearnPress", status_code=500, details=str(e))


async def _run_install(request, data: dict, user: dict, connection_id: int, correlation_id: str) -> dict:
    """Core install logic, returns a result dict. Used by both sync and streaming endpoints."""
    plugin_slug = data.get("plugin_slug", "learnpress")
    if not isinstance(plugin_slug, str) or not re.match(r'^[a-z0-9_-]+$', plugin_slug):
        return {"error": "invalid_plugin_slug", "message": "plugin_slug must match ^[a-z0-9_-]+$", "status_code": 400}

    log_extra = {"request_id": correlation_id, "plugin_slug": plugin_slug}

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
        if result and ("installPlugin" in result or any(k.lower().startswith("install") for k in result.keys())):
            logger.info("Plugin installed via GraphQL", extra=log_extra)
            return {"success": True, "method": "graphql", "result": result}
    except Exception as e:
        logger.debug("GraphQL install attempt failed: %s", e, extra=log_extra)

    # 2) Try REST endpoint (best-effort)
    connection = await connection_manager.get_connection(connection_id, user["id"])
    if not connection:
        return {"error": "connection_not_found", "message": "Connection not found", "status_code": 404}

    wp_url = connection["wp_url"].rstrip("/")
    wp_user = connection["wp_user"]
    wp_pass = connection.get("wp_app_password")
    auth_param = (wp_user, wp_pass) if wp_user and wp_pass else None

    if auth_param:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(f"{wp_url}/wp-json/wp/v2/plugins", json={"slug": plugin_slug}, auth=auth_param)
                if resp.status_code in (200, 201, 202, 204):
                    try:
                        body = resp.json()
                    except Exception:
                        body = None
                    logger.info("Plugin installed via REST", extra=log_extra)
                    return {"success": True, "method": "rest", "status": resp.status_code, "body": body}
                if resp.status_code in (401, 403):
                    return {"error": "unauthorized", "message": "Unauthorized to install plugin", "status_code": 403, "details": {"status": resp.status_code}}
            except httpx.HTTPError as e:
                logger.debug("REST install attempt failed: %s", e, extra=log_extra)
    else:
        logger.debug("Skipping REST install: missing credentials", extra=log_extra)

    # 3) Try mu-plugin bootstrap (for sites without WP-CLI or SSH)
    if auth_param:
        try:
            mu_result = await _try_mu_plugin_install(wp_url, auth_param, plugin_slug, log_extra)
            if mu_result:
                return mu_result
        except Exception as e:
            logger.debug("Mu-plugin install attempt failed: %s", e, extra=log_extra)

    # 4) Fallback: SSH-based setup script
    ssh_host = data.get("ssh_host") or data.get("host")
    if ssh_host:
        ssh_user = data.get("ssh_user") or data.get("user")
        port = int(data.get("ssh_port", 22))
        ssh_key = data.get("ssh_key")
        ssh_password = data.get("ssh_password")
        wp_path = data.get("wp_path")

        script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "setup-remote-wordpress.py"
        if not script_path.exists():
            return {"error": "setup_script_not_found", "message": "Setup script not found", "status_code": 500}

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

            logger.info("Running remote plugin install via SSH for %s", ssh_host, extra=log_extra)
            process = await run_subprocess_exec(
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
                logger.error("SSH install failed: %s", err, extra=log_extra)
                return {"error": "ssh_install_failed", "message": "SSH install failed", "status_code": 500, "details": err}

            logger.info("Plugin installed via SSH", extra=log_extra)
            return {"success": True, "method": "ssh", "output": output}
        except Exception as e:
            logger.error("SSH install exception: %s", e, exc_info=True, extra=log_extra)
            return {"error": "ssh_install_failed", "message": "SSH install failed", "status_code": 500, "details": str(e)}

    return {"error": "install_failed_no_credentials", "message": "Failed to install plugin via GraphQL, REST, and mu-plugin. Provide SSH credentials to attempt remote install.", "status_code": 500}


async def _try_mu_plugin_install(wp_url: str, auth_param: tuple, plugin_slug: str, log_extra: dict) -> Optional[dict]:
    """Try to install a plugin via a mu-plugin bootstrap endpoint.

    This works by uploading a temporary mu-plugin that exposes a REST endpoint
    to install plugins using WordPress's built-in plugin installer. Useful for
    environments without WP-CLI or SSH access.
    """
    mu_plugin_php = f'''<?php
/*
Plugin Name: Articulate Plugin Installer (temporary)
Description: Temporary mu-plugin for remote plugin installation. Auto-removes after use.
*/
add_action('rest_api_init', function() {{
    register_rest_route('articulate/v1', '/install-plugin', [
        'methods' => 'POST',
        'callback' => function($request) {{
            if (!current_user_can('install_plugins')) {{
                return new WP_Error('forbidden', 'Insufficient permissions', ['status' => 403]);
            }}
            $slug = sanitize_text_field($request->get_param('slug'));
            if (empty($slug)) {{
                return new WP_Error('missing_slug', 'Plugin slug required', ['status' => 400]);
            }}
            require_once ABSPATH . 'wp-admin/includes/plugin-install.php';
            require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
            $api = plugins_api('plugin_information', ['slug' => $slug, 'fields' => ['sections' => false]]);
            if (is_wp_error($api)) {{
                return new WP_Error('api_error', $api->get_error_message(), ['status' => 500]);
            }}
            $upgrader = new Plugin_Upgrader(new Automatic_Upgrader_Skin());
            $result = $upgrader->install($api->download_link);
            if (is_wp_error($result)) {{
                return new WP_Error('install_error', $result->get_error_message(), ['status' => 500]);
            }}
            // Activate the plugin
            $plugin_file = $upgrader->plugin_info();
            if ($plugin_file) {{
                activate_plugin($plugin_file);
            }}
            // Self-cleanup: remove this mu-plugin
            @unlink(__FILE__);
            return ['success' => true, 'plugin' => $slug, 'activated' => !empty($plugin_file)];
        }},
        'permission_callback' => '__return_true',
    ]]);
}});
'''

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Upload mu-plugin via WordPress REST media endpoint
        # Try the articulate-specific upload endpoint first
        try:
            resp = await client.post(
                f"{wp_url}/wp-json/articulate/v1/install-plugin",
                json={"slug": plugin_slug},
                auth=auth_param,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                if data.get("success"):
                    logger.info("Plugin installed via mu-plugin endpoint", extra=log_extra)
                    return {"success": True, "method": "mu-plugin", "result": data}
        except httpx.HTTPError:
            pass  # Endpoint doesn't exist yet, that's expected

    # The mu-plugin isn't installed yet. For now return None to fall through.
    # Full implementation would upload the mu-plugin PHP file via SSH or FTP,
    # then call the REST endpoint. This is the detection/fallback path.
    return None


async def install_learnpress_endpoint(request):
    """Install LearnPress on a connected WordPress site.

    Attempt order:
      1. GraphQL mutation (if exposed by the site)
      2. REST endpoint (if the site exposes plugin management)
      3. Mu-plugin bootstrap (for sites without WP-CLI)
      4. SSH-based setup script (requires ssh credentials in request)
    """
    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return error_response("session_required", "Session required", status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return error_response("invalid_session", "Invalid session", status_code=401)

        connection_id = int(request.path_params.get("id"))
        data = await request.json()
        correlation_id = _get_correlation_id(request)

        result = await _run_install(request, data, user, connection_id, correlation_id)

        # Convert result dict to appropriate response
        if result.get("error"):
            return error_response(
                result["error"],
                result["message"],
                status_code=result.get("status_code", 500),
                details=result.get("details"),
            )
        return JSONResponse(result)

    except Exception as e:
        logger.error("Install LearnPress error: %s", e, exc_info=True)
        return error_response("install_error", "Failed to install LearnPress", status_code=500, details=str(e))


async def install_learnpress_stream_endpoint(request):
    """SSE streaming endpoint for plugin installation with live progress updates.

    Returns Server-Sent Events as the install progresses through each method.
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return error_response("session_required", "Session required", status_code=401)

    user = await UserManager.get_user_from_session(session_id)
    if not user:
        return error_response("invalid_session", "Invalid session", status_code=401)

    connection_id = int(request.path_params.get("id"))
    data = await request.json()
    correlation_id = _get_correlation_id(request)
    plugin_slug = data.get("plugin_slug", "learnpress")

    if not isinstance(plugin_slug, str) or not re.match(r'^[a-z0-9_-]+$', plugin_slug):
        return error_response("invalid_plugin_slug", "plugin_slug must match ^[a-z0-9_-]+$", status_code=400)

    async def event_stream():
        """Generate SSE events for each install stage."""
        def sse_event(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        yield sse_event("progress", {"stage": "start", "message": f"Installing {plugin_slug}...", "correlation_id": correlation_id})

        log_extra = {"request_id": correlation_id, "plugin_slug": plugin_slug}

        # Stage 1: GraphQL
        yield sse_event("progress", {"stage": "graphql", "message": "Trying GraphQL mutation..."})
        try:
            client = await get_graphql_client(connection_id, user["id"])
            mutation = """
            mutation InstallPlugin($slug: String!) {
              installPlugin(slug: $slug) { success message }
            }
            """
            result = await client.mutate(mutation, {"slug": plugin_slug})
            if result and ("installPlugin" in result or any(k.lower().startswith("install") for k in result.keys())):
                yield sse_event("complete", {"success": True, "method": "graphql", "result": result})
                return
        except Exception as e:
            yield sse_event("progress", {"stage": "graphql", "message": f"GraphQL unavailable: {e}", "fallback": True})

        # Stage 2: REST
        yield sse_event("progress", {"stage": "rest", "message": "Trying REST plugin install..."})
        connection = await connection_manager.get_connection(connection_id, user["id"])
        if not connection:
            yield sse_event("error", {"error": "connection_not_found", "message": "Connection not found"})
            return

        wp_url = connection["wp_url"].rstrip("/")
        wp_user = connection["wp_user"]
        wp_pass = connection.get("wp_app_password")
        auth_param = (wp_user, wp_pass) if wp_user and wp_pass else None

        if auth_param:
            try:
                async with httpx.AsyncClient(timeout=30.0) as http:
                    resp = await http.post(f"{wp_url}/wp-json/wp/v2/plugins", json={"slug": plugin_slug}, auth=auth_param)
                    if resp.status_code in (200, 201, 202, 204):
                        yield sse_event("complete", {"success": True, "method": "rest", "status": resp.status_code})
                        return
                    if resp.status_code in (401, 403):
                        yield sse_event("progress", {"stage": "rest", "message": "Unauthorized for REST install", "fallback": True})
                    else:
                        yield sse_event("progress", {"stage": "rest", "message": f"REST returned {resp.status_code}", "fallback": True})
            except httpx.HTTPError as e:
                yield sse_event("progress", {"stage": "rest", "message": f"REST failed: {e}", "fallback": True})
        else:
            yield sse_event("progress", {"stage": "rest", "message": "No REST credentials, skipping", "fallback": True})

        # Stage 3: Mu-plugin
        if auth_param:
            yield sse_event("progress", {"stage": "mu-plugin", "message": "Trying mu-plugin bootstrap..."})
            try:
                mu_result = await _try_mu_plugin_install(wp_url, auth_param, plugin_slug, log_extra)
                if mu_result:
                    yield sse_event("complete", mu_result)
                    return
                yield sse_event("progress", {"stage": "mu-plugin", "message": "Mu-plugin endpoint not available", "fallback": True})
            except Exception as e:
                yield sse_event("progress", {"stage": "mu-plugin", "message": f"Mu-plugin failed: {e}", "fallback": True})

        # Stage 4: SSH
        ssh_host = data.get("ssh_host") or data.get("host")
        if ssh_host:
            yield sse_event("progress", {"stage": "ssh", "message": f"Connecting to {ssh_host} via SSH..."})

            ssh_user = data.get("ssh_user") or data.get("user")
            port = int(data.get("ssh_port", 22))
            ssh_key = data.get("ssh_key")
            ssh_password = data.get("ssh_password")
            wp_path = data.get("wp_path")

            script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "setup-remote-wordpress.py"
            if not script_path.exists():
                yield sse_event("error", {"error": "setup_script_not_found", "message": "Setup script not found"})
                return

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

                yield sse_event("progress", {"stage": "ssh", "message": "Running WP-CLI install..."})

                process = await run_subprocess_exec(
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
                    yield sse_event("error", {"error": "ssh_install_failed", "message": err})
                    return

                yield sse_event("complete", {"success": True, "method": "ssh", "output": output})
                return
            except Exception as e:
                if key_file:
                    try:
                        Path(key_file.name).unlink()
                    except Exception:
                        pass
                yield sse_event("error", {"error": "ssh_install_failed", "message": str(e)})
                return

        yield sse_event("error", {
            "error": "install_failed_no_credentials",
            "message": "All install methods failed. Provide SSH credentials to attempt remote install.",
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Correlation-ID": correlation_id,
        },
    )


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
