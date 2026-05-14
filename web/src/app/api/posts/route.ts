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

export async function GET(request: NextRequest) {
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

    const searchParams = request.nextUrl.searchParams;
    const status = searchParams.get("status") || "any";
    const search = searchParams.get("search") || undefined;
    const perPage = parseInt(searchParams.get("per_page") || "20", 10);

    const result = await callMCPTool(
      "get_posts",
      {
        status,
        per_page: perPage,
        ...(search ? { search } : {}),
      },
      { ...authHeaders, "X-Request-ID": requestId },
      { requestId, allowedAccess: ["Read"] }
    );

    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "INTERNAL_ERROR",
      message,
      remediation: "Retry; if this persists, check MCP server health and logs.",
      requestId,
      retryable: true,
    });
  }
}

export async function POST(request: NextRequest) {
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

    const body = await request.json();
    const { title, content, status, type } = body;

    // Validate required fields
    if (!title || typeof title !== "string") {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Title is required and must be a string",
        remediation: "Provide a non-empty title.",
        requestId,
      });
    }

    // Validate optional fields
    if (content && typeof content !== "string") {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "Content must be a string",
        remediation: "Send content as plain string.",
        requestId,
      });
    }

    // Validate status enum
    const validStatuses = ["draft", "publish", "pending", "private"];
    const postStatus = status || "draft";
    if (!validStatuses.includes(postStatus)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: `Invalid status. Must be one of: ${validStatuses.join(", ")}`,
        remediation: "Use one of the allowed status values.",
        requestId,
      });
    }

    // Validate type enum
    const validTypes = ["post", "page"];
    const postType = type || "post";
    if (!validTypes.includes(postType)) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: `Invalid type. Must be one of: ${validTypes.join(", ")}`,
        remediation: "Use 'post' or 'page'.",
        requestId,
      });
    }

    // Write guard: ensure MCP health before mutating requests.
    const mcpHealth = await fetch(`${process.env.MCP_SERVER_URL || "http://localhost:8000"}/health`);
    if (!mcpHealth.ok) {
      return apiError(503, {
        code: "UPSTREAM_UNAVAILABLE",
        message: "MCP server health check failed",
        remediation: "Wait for the backend to become healthy, then retry.",
        requestId,
        retryable: true,
      });
    }
    const requiredCap = postType === "page" ? "edit_pages" : "edit_posts";
    const canWrite = await hasCapability(authHeaders, requiredCap);
    if (!canWrite) {
      return apiError(403, {
        code: "CAPABILITY_MISSING",
        message: `Missing required WordPress capability: ${requiredCap}`,
        remediation: "Use an account/role with the required capability or ask an administrator.",
        requestId,
      });
    }

    const result = await callMCPTool(
      "create_post",
      {
        title: title.trim(),
        content: content?.trim() || "",
        status: postStatus,
        post_type: postType,
      },
      { ...authHeaders, "X-Request-ID": requestId, "Idempotency-Key": getOrCreateIdempotencyKey(request) },
      { requestId, idempotencyKey: getOrCreateIdempotencyKey(request), retries: 2 }
    );

    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Check WordPress capabilities, endpoint availability, and request payload.",
      requestId,
      retryable: true,
    });
  }
}
