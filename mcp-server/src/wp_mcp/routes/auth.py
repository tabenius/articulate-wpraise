"""Authentication endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def register_endpoint(request):
    """User registration endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name", "")

        user = await UserManager.register_user(email, password, name)

        # Log successful registration
        await AuditLog.log_auth_event(
            event_type="register",
            status="success",
            user_id=user["id"],
            email=email,
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"New user registered: {email}",
        )

        return JSONResponse(user, status_code=201)
    except ValueError as e:
        # Log failed registration (validation error)
        await AuditLog.log_auth_event(
            event_type="register",
            status="failure",
            email=data.get("email") if 'data' in locals() else None,
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Registration failed: {str(e)}",
        )
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Registration error: %s", e)
        await AuditLog.log_auth_event(
            event_type="register",
            status="error",
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Registration error: {str(e)}",
        )
        return JSONResponse({"error": "Registration failed"}, status_code=500)


async def login_endpoint(request):
    """User login endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        result = await UserManager.authenticate(email, password)
        if result:
            # Log successful login
            await AuditLog.log_auth_event(
                event_type="login",
                status="success",
                user_id=result["user"]["id"],
                email=email,
                ip_address=client_ip,
                user_agent=user_agent,
                message=f"User logged in: {email}",
            )
            return JSONResponse(result)
        else:
            # Log failed login
            await AuditLog.log_auth_event(
                event_type="login",
                status="failure",
                email=email,
                ip_address=client_ip,
                user_agent=user_agent,
                message=f"Login failed for {email}: Invalid credentials",
            )
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    except Exception as e:
        logger.error("Login error: %s", e)
        await AuditLog.log_auth_event(
            event_type="login",
            status="error",
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Login error: {str(e)}",
        )
        return JSONResponse({"error": "Login failed"}, status_code=500)


async def logout_endpoint(request):
    """User logout endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session ID required"}, status_code=400)

        # Get user info before logout
        user = await UserManager.get_user_from_session(session_id)

        success = await UserManager.logout(session_id)
        if success:
            # Log successful logout
            if user:
                await AuditLog.log_auth_event(
                    event_type="logout",
                    status="success",
                    user_id=user["id"],
                    email=user["email"],
                    ip_address=client_ip,
                    user_agent=user_agent,
                    message=f"User logged out: {user['email']}",
                )
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Invalid session"}, status_code=404)
    except Exception as e:
        logger.error("Logout error: %s", e)
        return JSONResponse({"error": "Logout failed"}, status_code=500)


async def me_endpoint(request):
    """Get current user info from session."""
    from wp_mcp.user_manager import UserManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session ID required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if user:
            return JSONResponse(user)
        else:
            return JSONResponse({"error": "Invalid or expired session"}, status_code=401)
    except Exception as e:
        logger.error("Get user error: %s", e)
        return JSONResponse({"error": "Failed to get user"}, status_code=500)
