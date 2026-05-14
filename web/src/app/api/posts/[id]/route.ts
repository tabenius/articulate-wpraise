import { NextRequest } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";
import { apiError, apiOk } from "@/lib/route-helpers";
import { getOrCreateIdempotencyKey, getOrCreateRequestId } from "@/lib/request-meta";

async function hasCapability(authHeaders: Record<string, string>, capability: string): Promise<boolean> {
  const capRes = await fetch(`${process.env.MCP_SERVER_URL || "http://localhost:8000"}/capabilities`, {
    headers: { ...authHeaders, "Content-Type": "application/json" },
  });
  if (!capRes.ok) return false;
  const caps = await capRes.json();
  const list = Array.isArray(caps?.capabilities) ? caps.capabilities : [];
  return list.includes(capability);
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const requestId = getOrCreateRequestId(request);
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in again and retry.",
        requestId,
      });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Invalid post ID",
        remediation: "Use a numeric post id.",
        requestId,
      });
    }

    const type = request.nextUrl.searchParams.get("type") || "post";
    const tool = type === "page" ? "get_page" : "get_post";
    const result = await callMCPTool(tool, { post_id: postId }, { ...authHeaders, "X-Request-ID": requestId }, { requestId, allowedAccess: ["Read"] });
    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "INTERNAL_ERROR",
      message,
      remediation: "Retry; if this persists, inspect backend logs with request ID.",
      requestId,
      retryable: true,
    });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const requestId = getOrCreateRequestId(request);
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in again and retry.",
        requestId,
      });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Invalid post ID",
        remediation: "Use a numeric post id.",
        requestId,
      });
    }

    const body = await request.json();
    const {
      title,
      content,
      status,
      featured_image_id,
      category_ids,
      tag_ids,
      date,
    } = body;

    const mcpHealth = await fetch(`${process.env.MCP_SERVER_URL || "http://localhost:8000"}/health`);
    if (!mcpHealth.ok) {
      return apiError(503, {
        code: "UPSTREAM_UNAVAILABLE",
        message: "MCP server health check failed",
        remediation: "Wait for MCP/WordPress services to be healthy and retry.",
        requestId,
        retryable: true,
      });
    }
    const canWrite = await hasCapability(authHeaders, "edit_posts");
    if (!canWrite) {
      return apiError(403, {
        code: "CAPABILITY_MISSING",
        message: "Missing required WordPress capability: edit_posts",
        remediation: "Use an account/role with edit_posts.",
        requestId,
      });
    }

    const idempotencyKey = getOrCreateIdempotencyKey(request);
    const result = await callMCPTool("update_post", {
      post_id: postId,
      ...(title !== undefined ? { title } : {}),
      ...(content !== undefined ? { content } : {}),
      ...(status !== undefined ? { status } : {}),
      ...(featured_image_id !== undefined ? { featured_image_id } : {}),
      ...(category_ids !== undefined ? { category_ids } : {}),
      ...(tag_ids !== undefined ? { tag_ids } : {}),
      ...(date !== undefined ? { date } : {}),
    }, { ...authHeaders, "X-Request-ID": requestId, "Idempotency-Key": idempotencyKey }, { requestId, idempotencyKey, retries: 2 });

    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Check payload validity and WordPress permissions for this action.",
      requestId,
      retryable: true,
    });
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const requestId = getOrCreateRequestId(request);
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in again and retry.",
        requestId,
      });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Invalid post ID",
        remediation: "Use a numeric post id.",
        requestId,
      });
    }

    const body = await request.json();
    const {
      title,
      content,
      status,
      featured_image_id,
      category_ids,
      tag_ids,
      date,
    } = body;
    const mcpHealth = await fetch(`${process.env.MCP_SERVER_URL || "http://localhost:8000"}/health`);
    if (!mcpHealth.ok) {
      return apiError(503, {
        code: "UPSTREAM_UNAVAILABLE",
        message: "MCP server health check failed",
        remediation: "Wait for MCP/WordPress services to be healthy and retry.",
        requestId,
        retryable: true,
      });
    }
    const canWrite = await hasCapability(authHeaders, "edit_posts");
    if (!canWrite) {
      return apiError(403, {
        code: "CAPABILITY_MISSING",
        message: "Missing required WordPress capability: edit_posts",
        remediation: "Use an account/role with edit_posts.",
        requestId,
      });
    }

    const idempotencyKey = getOrCreateIdempotencyKey(request);
    const result = await callMCPTool("update_post", {
      post_id: postId,
      ...(title !== undefined ? { title } : {}),
      ...(content !== undefined ? { content } : {}),
      ...(status !== undefined ? { status } : {}),
      ...(featured_image_id !== undefined ? { featured_image_id } : {}),
      ...(category_ids !== undefined ? { category_ids } : {}),
      ...(tag_ids !== undefined ? { tag_ids } : {}),
      ...(date !== undefined ? { date } : {}),
    }, { ...authHeaders, "X-Request-ID": requestId, "Idempotency-Key": idempotencyKey }, { requestId, idempotencyKey, retries: 2 });

    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Check payload validity and WordPress permissions for this action.",
      requestId,
      retryable: true,
    });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const requestId = getOrCreateRequestId(_request);
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in again and retry.",
        requestId,
      });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Invalid post ID",
        remediation: "Use a numeric post id.",
        requestId,
      });
    }
    const confirmDelete = _request.headers.get("x-confirm-delete");
    if (confirmDelete !== "true") {
      return apiError(409, {
        code: "WRITE_GUARD_FAILED",
        message: "Delete confirmation header missing",
        remediation: "Repeat delete with header x-confirm-delete: true",
        requestId,
      });
    }
    const canDelete = await hasCapability(authHeaders, "delete_posts");
    if (!canDelete) {
      return apiError(403, {
        code: "CAPABILITY_MISSING",
        message: "Missing required WordPress capability: delete_posts",
        remediation: "Use an account/role with delete_posts.",
        requestId,
      });
    }
    const idempotencyKey = getOrCreateIdempotencyKey(_request);
    const result = await callMCPTool("delete_post", { post_id: postId }, { ...authHeaders, "X-Request-ID": requestId, "Idempotency-Key": idempotencyKey }, { requestId, idempotencyKey, retries: 2 });
    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Check WordPress delete capabilities and upstream availability.",
      requestId,
      retryable: true,
    });
  }
}
