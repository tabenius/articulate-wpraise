"""REST endpoints for tenant management."""

import os
import logging
from starlette.requests import Request
from starlette.responses import JSONResponse

from wp_mcp.database import db
from wp_mcp.user_manager import UserManager
from wp_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)

_manager = None


def get_manager():
    global _manager
    if _manager is None:
        from wp_mcp.tenants.manager import TenantManager
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise RuntimeError("ENCRYPTION_KEY required for tenant management")
        _manager = TenantManager(
            encryption_key=encryption_key,
            template_dir=os.getenv("TEMPLATE_DIR", "/app/templates"),
            compose_output_dir=os.getenv("COMPOSE_OUTPUT_DIR", "/app/tenants"),
        )
    return _manager


async def _get_user(request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return None
    return await UserManager.get_user_from_session(session_id)


async def create_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return JSONResponse({"error": "name is required"}, status_code=400)
        result = await get_manager().create_tenant(name=name, owner_user_id=user["id"])
        return JSONResponse(sanitize_for_json(result), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Create tenant error: %s", e)
        return JSONResponse({"error": "Failed to create tenant"}, status_code=500)


async def list_tenants_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        tenants = await get_manager().list_tenants(owner_user_id=user["id"])
        return JSONResponse(sanitize_for_json({"tenants": tenants}))
    except Exception as e:
        logger.error("List tenants error: %s", e)
        return JSONResponse({"error": "Failed to list tenants"}, status_code=500)


async def get_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        tenant = await get_manager().get_tenant(tenant_id)
        if not tenant:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse(sanitize_for_json(tenant))
    except Exception as e:
        logger.error("Get tenant error: %s", e)
        return JSONResponse({"error": "Failed to get tenant"}, status_code=500)


async def delete_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        success = await get_manager().delete_tenant(tenant_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error("Delete tenant error: %s", e)
        return JSONResponse({"error": "Failed to delete tenant"}, status_code=500)


async def update_default_view_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        data = await request.json()
        view = data.get("default_view", "")
        await get_manager().set_default_view(tenant_id, view)
        return JSONResponse({"success": True, "default_view": view})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update default view error: %s", e)
        return JSONResponse({"error": "Failed to update"}, status_code=500)


async def add_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        data = await request.json()
        domain_id = await get_manager().add_custom_domain(
            tenant_id=tenant_id,
            external_domain=data["external_domain"],
            target_view=data["target_view"],
        )
        return JSONResponse({"success": True, "domain_id": domain_id}, status_code=201)
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Add domain error: %s", e)
        return JSONResponse({"error": "Failed to add domain"}, status_code=500)


async def remove_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    domain_id = int(request.path_params["domain_id"])
    try:
        success = await get_manager().remove_custom_domain(domain_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error("Remove domain error: %s", e)
        return JSONResponse({"error": "Failed to remove domain"}, status_code=500)


async def verify_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    domain_id = int(request.path_params["domain_id"])
    try:
        success = await get_manager().verify_custom_domain(domain_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True, "verified": True})
    except Exception as e:
        logger.error("Verify domain error: %s", e)
        return JSONResponse({"error": "Failed to verify"}, status_code=500)
