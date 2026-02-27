"""Endpoints for LearnPress detection and management."""

from __future__ import annotations

import asyncio
import logging
import json
import tempfile
from pathlib import Path

import httpx
from starlette.responses import JSONResponse

from articulate_mcp.user_manager import UserManager
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.graphql.client import get_graphql_client, GraphQLError

logger = logging.getLogger(__name__)


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
