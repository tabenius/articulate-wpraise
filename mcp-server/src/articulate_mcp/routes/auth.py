"""Authentication endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def register_endpoint(request):
    """User registration endpoint."""
    from articulate_mcp.audit import AuditLog
    from articulate_mcp.user_manager import UserManager

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
    from articulate_mcp.audit import AuditLog
    from articulate_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        result = await UserManager.authenticate(email, password)
        if result and result.get("error") == "email_not_verified":
            return JSONResponse(
                {"error": "email_not_verified", "email": result["email"]},
                status_code=403,
            )
        if result and "session_id" in result:
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
    from articulate_mcp.audit import AuditLog
    from articulate_mcp.user_manager import UserManager

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
    from articulate_mcp.user_manager import UserManager

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


async def verify_email_endpoint(request):
    """Verify email address using token."""
    from articulate_mcp.user_manager import UserManager

    try:
        data = await request.json()
        token = data.get("token")
        if not token:
            return JSONResponse({"error": "Token required"}, status_code=400)

        success = await UserManager.verify_email(token)
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Invalid or expired token"}, status_code=400)
    except Exception as e:
        logger.error("Verify email error: %s", e)
        return JSONResponse({"error": "Verification failed"}, status_code=500)


async def resend_verification_endpoint(request):
    """Resend verification email."""
    from articulate_mcp.user_manager import UserManager

    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            return JSONResponse({"error": "Email required"}, status_code=400)

        await UserManager.resend_verification(email)
        # Always return success to not leak user existence
        return JSONResponse({"success": True, "message": "If the email is registered, a verification link has been sent."})
    except Exception as e:
        logger.error("Resend verification error: %s", e)
        return JSONResponse({"error": "Failed to resend"}, status_code=500)


async def forgot_password_endpoint(request):
    """Request a password reset email."""
    from articulate_mcp.user_manager import UserManager

    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            return JSONResponse({"error": "Email required"}, status_code=400)

        await UserManager.request_password_reset(email)
        return JSONResponse({"success": True, "message": "If the email is registered, a reset link has been sent."})
    except Exception as e:
        logger.error("Forgot password error: %s", e)
        return JSONResponse({"error": "Failed to send reset email"}, status_code=500)


async def reset_password_endpoint(request):
    """Reset password with token."""
    from articulate_mcp.user_manager import UserManager

    try:
        data = await request.json()
        token = data.get("token")
        password = data.get("password")
        if not token or not password:
            return JSONResponse({"error": "Token and password required"}, status_code=400)

        success = await UserManager.reset_password(token, password)
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Invalid or expired token"}, status_code=400)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Reset password error: %s", e)
        return JSONResponse({"error": "Password reset failed"}, status_code=500)


async def wp_login_token_endpoint(request):
    """Generate a one-time WP-Admin login token for a tenant."""
    from articulate_mcp.user_manager import UserManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Authentication required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        tenant_id = data.get("tenant_id")
        if not tenant_id:
            return JSONResponse({"error": "tenant_id required"}, status_code=400)

        token = await UserManager.create_wp_login_token(user["id"], tenant_id)

        return JSONResponse({"token": token})
    except Exception as e:
        logger.error("WP login token error: %s", e)
        return JSONResponse({"error": "Failed to create login token"}, status_code=500)


async def validate_wp_login_token_endpoint(request):
    """Validate a one-time WP-Admin login token (called by tenant WordPress)."""
    from articulate_mcp.user_manager import UserManager

    try:
        data = await request.json()
        token = data.get("token")
        if not token:
            return JSONResponse({"valid": False, "error": "Token required"}, status_code=400)

        result = await UserManager.validate_wp_login_token(token)
        if result:
            return JSONResponse({"valid": True, **result})
        else:
            return JSONResponse({"valid": False}, status_code=401)
    except Exception as e:
        logger.error("Validate WP login token error: %s", e)
        return JSONResponse({"valid": False, "error": "Validation failed"}, status_code=500)
