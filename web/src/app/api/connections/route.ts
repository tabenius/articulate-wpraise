import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { NextRequest } from "next/server";
import { apiError, apiOk } from "@/lib/route-helpers";
import { getOrCreateIdempotencyKey, getOrCreateRequestId } from "@/lib/request-meta";

function isValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export async function GET(request: NextRequest) {
  const requestId = getOrCreateRequestId(request);
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in and retry.",
        requestId,
      });
    }

    // Call MCP server to get connections
    const response = await fetch(`${MCP_SERVER_URL}/connections`, {
      method: "GET",
      headers: {
        "X-Session-ID": sessionCookie.value,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return apiError(response.status, {
        code: "UPSTREAM_REJECTED",
        message: error.message || "Failed to get connections",
        remediation: "Check MCP server and WordPress connection health.",
        requestId,
      });
    }

    const data = await response.json();
    return apiOk(data, requestId);
  } catch (error) {
    console.error("Get connections error:", error);
    return apiError(500, {
      code: "INTERNAL_ERROR",
      message: "Failed to get connections",
      remediation: "Retry request and inspect server logs.",
      requestId,
      retryable: true,
    });
  }
}

export async function POST(request: NextRequest) {
  const requestId = getOrCreateRequestId(request);
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return apiError(401, {
        code: "AUTH_REQUIRED",
        message: "Authentication required",
        remediation: "Sign in and retry.",
        requestId,
      });
    }

    const { name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password } =
      await request.json();

    // Validate input
    if (!name || !wp_url || !wp_graphql_endpoint || !wp_user || !wp_app_password) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "All fields are required",
        remediation: "Provide name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password.",
        requestId,
      });
    }
    if (!isValidHttpUrl(String(wp_url))) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "wp_url must be a valid http/https URL",
        remediation: "Use a full URL such as https://example.com.",
        requestId,
      });
    }
    if (!isValidHttpUrl(String(wp_graphql_endpoint))) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "wp_graphql_endpoint must be a valid http/https URL",
        remediation: "Use a full URL such as https://example.com/graphql.",
        requestId,
      });
    }
    if (!String(wp_graphql_endpoint).includes("/graphql")) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "wp_graphql_endpoint should include '/graphql'",
        remediation: "Append /graphql to your endpoint.",
        requestId,
      });
    }
    if (String(wp_app_password).trim().length < 8) {
      return apiError(400, {
        code: "VALIDATION_ERROR",
        message: "wp_app_password appears too short",
        remediation: "Generate a WordPress Application Password and use it verbatim.",
        requestId,
      });
    }

    // Call MCP server to add connection
    const response = await fetch(`${MCP_SERVER_URL}/connections`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
        "X-Request-ID": requestId,
        "Idempotency-Key": getOrCreateIdempotencyKey(request),
      },
      body: JSON.stringify({
        name,
        wp_url,
        wp_graphql_endpoint,
        wp_user,
        wp_app_password,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      return apiError(response.status, {
        code: "UPSTREAM_REJECTED",
        message: error.message || "Failed to add connection",
        remediation: "Verify WordPress URL, GraphQL endpoint, credentials, and capabilities.",
        requestId,
      });
    }

    const data = await response.json();
    return apiOk(data, requestId);
  } catch (error) {
    console.error("Add connection error:", error);
    return apiError(500, {
      code: "INTERNAL_ERROR",
      message: "Failed to add connection",
      remediation: "Retry request and inspect server logs with request ID.",
      requestId,
      retryable: true,
    });
  }
}
