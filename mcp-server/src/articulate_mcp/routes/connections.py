"""WordPress connection management endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

from starlette.responses import JSONResponse

from articulate_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)


async def get_connections_endpoint(request):
    """Get user's WordPress connections."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connections = await connection_manager.get_connections(user["id"])
        return JSONResponse(sanitize_for_json(connections))
    except Exception as e:
        logger.error("Get connections error: %s", e)
        return JSONResponse({"error": "Failed to get connections"}, status_code=500)


async def add_connection_endpoint(request):
    """Add new WordPress connection."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        connection = await connection_manager.add_connection(
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse(sanitize_for_json(connection), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Add connection error: %s", e)
        return JSONResponse({"error": "Failed to add connection"}, status_code=500)


async def update_connection_endpoint(request):
    """Update WordPress connection."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Get connection ID from path
        connection_id = int(request.path_params.get("id"))
        data = await request.json()

        await connection_manager.update_connection(
            connection_id=connection_id,
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update connection error: %s", e)
        return JSONResponse({"error": "Failed to update connection"}, status_code=500)


async def delete_connection_endpoint(request):
    """Delete WordPress connection."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.delete_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Delete connection error: %s", e)
        return JSONResponse({"error": "Failed to delete connection"}, status_code=500)


async def activate_connection_endpoint(request):
    """Set connection as active."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.set_active_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Activate connection error: %s", e)
        return JSONResponse({"error": "Failed to activate connection"}, status_code=500)


async def setup_remote_wordpress_endpoint(request):
    """Setup remote WordPress via SSH and optionally create connection."""
    from articulate_mcp.user_manager import UserManager
    from articulate_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        host = data.get("host")
        ssh_user = data.get("user")
        port = data.get("port", 22)
        ssh_key = data.get("ssh_key")  # SSH private key content
        ssh_password = data.get("ssh_password")
        wp_path = data.get("wp_path")  # Optional WordPress directory path
        discover_only = data.get("discover", False)  # Discovery mode
        auto_create = data.get("auto_create", False)  # Auto-create connection

        # Defensive: validate inputs
        if not host or not ssh_user:
            return JSONResponse(
                {"error": "host and user are required"},
                status_code=400
            )

        if not ssh_key and not ssh_password:
            return JSONResponse(
                {"error": "Either ssh_key or ssh_password is required"},
                status_code=400
            )

        # Defensive: validate port
        if not isinstance(port, int) or port < 1 or port > 65535:
            return JSONResponse(
                {"error": "Invalid port number"},
                status_code=400
            )

        # Defensive: sanitize wp_path if provided
        if wp_path:
            if not isinstance(wp_path, str) or not wp_path.startswith('/'):
                return JSONResponse(
                    {"error": "Invalid wp_path: must be absolute path"},
                    status_code=400
                )

        # Find the setup script
        script_path = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "setup-remote-wordpress.py"
        if not script_path.exists():
            return JSONResponse(
                {"error": "Setup script not found"},
                status_code=500
            )

        # Prepare command
        cmd = ["python3", str(script_path), "--host", host, "--user", ssh_user, "--port", str(port)]

        # Add discovery flag if requested
        if discover_only:
            cmd.append("--discover")

        # Add wp_path if provided
        if wp_path and not discover_only:
            cmd.extend(["--wp-path", wp_path])

        # Handle SSH key (write to temp file)
        key_file = None
        if ssh_key:
            key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
            key_file.write(ssh_key)
            key_file.close()
            # Set proper permissions for SSH key
            Path(key_file.name).chmod(0o600)
            cmd.extend(["--key", key_file.name])
        else:
            cmd.extend(["--password", ssh_password])

        # Include plugins list if provided (comma-separated string or list)
        plugins = data.get("plugins")
        if plugins:
            # Accept list or comma-separated string
            if isinstance(plugins, list):
                plugins_str = ",".join([p for p in plugins if p])
            else:
                plugins_str = str(plugins)
            if plugins_str:
                cmd.extend(["--plugins", plugins_str])

        # Run setup script
        logger.info(f"Running remote WordPress setup for {host}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Clean up temp key file
        if key_file:
            try:
                Path(key_file.name).unlink()
            except (OSError, FileNotFoundError) as e:
                logger.debug(f"Failed to remove temp key file: {e}")
                pass

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Setup failed"
            logger.error(f"Remote setup failed: {error_msg}")
            return JSONResponse(
                {"error": "Remote setup failed", "details": error_msg},
                status_code=500
            )

        # Parse output
        output = stdout.decode()
        logger.info(f"Remote setup output: {output}")

        # Extract JSON from output
        try:
            # Find the JSON block in output
            json_start = output.find('{')
            json_end = output.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                result = json.loads(output[json_start:json_end])
            else:
                return JSONResponse(
                    {"error": "Failed to parse output"},
                    status_code=500
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse output: {e}")
            return JSONResponse(
                {"error": "Failed to parse output", "details": output},
                status_code=500
            )

        # Handle discovery mode
        if discover_only:
            return JSONResponse({
                "success": True,
                "discover": True,
                "installations": result.get("installations", []),
                "count": result.get("count", 0)
            })

        # Handle setup mode
        connection_info = result

        # Auto-create connection if requested
        connection = None
        if auto_create:
            try:
                connection = await connection_manager.add_connection(
                    user_id=user["id"],
                    name=connection_info.get("name"),
                    wp_url=connection_info.get("wp_url"),
                    wp_graphql_endpoint=connection_info.get("wp_graphql_endpoint"),
                    wp_user=connection_info.get("wp_user"),
                    wp_app_password=connection_info.get("wp_app_password"),
                )
                logger.info(f"Auto-created connection {connection['id']} for user {user['id']}")
            except Exception as e:
                logger.error(f"Failed to auto-create connection: {e}")
                # Don't fail the whole request if connection creation fails

        return JSONResponse({
            "success": True,
            "connection_info": connection_info,
            "connection": connection,
            "output": output
        }, status_code=201)

    except Exception as e:
        logger.error(f"Remote WordPress setup error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": "Setup failed", "details": str(e)},
            status_code=500
        )
