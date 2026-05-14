import { NextRequest } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";
import { apiError, apiOk } from "@/lib/route-helpers";
import { getOrCreateIdempotencyKey, getOrCreateRequestId } from "@/lib/request-meta";

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
    const postId = parseInt(
      request.nextUrl.searchParams.get("postId") || "0",
      10
    );
    if (!postId) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "postId is required",
        remediation: "Provide numeric postId query param.",
        requestId,
      });
    }

    const result = await callMCPTool("get_blocks", { post_id: postId }, { ...authHeaders, "X-Request-ID": requestId }, { requestId, allowedAccess: ["Read"] });
    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Check MCP/WordPress connectivity and post permissions.",
      requestId,
      retryable: true,
    });
  }
}

export async function PUT(request: NextRequest) {
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
    const { postId, blocks } = body;

    if (!postId || !blocks) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "postId and blocks are required",
        remediation: "Provide both postId and blocks array.",
        requestId,
      });
    }
    const idempotencyKey = getOrCreateIdempotencyKey(request);

    const result = await callMCPTool("update_blocks", {
      post_id: postId,
      blocks,
    }, { ...authHeaders, "X-Request-ID": requestId, "Idempotency-Key": idempotencyKey }, { requestId, idempotencyKey, retries: 2 });

    return apiOk(result, requestId);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return apiError(500, {
      code: "UPSTREAM_REJECTED",
      message,
      remediation: "Retry save; if persistent, validate WPGraphQL content blocks support.",
      requestId,
      retryable: true,
    });
  }
}
