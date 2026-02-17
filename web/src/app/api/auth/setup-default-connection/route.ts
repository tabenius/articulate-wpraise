import { NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

/**
 * Auto-create default WordPress connection for new users
 * Called automatically on first login
 */
export async function POST() {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    // Check if user already has connections
    const checkResponse = await fetch(`${MCP_SERVER_URL}/connections`, {
      headers: authHeaders,
    });

    if (checkResponse.ok) {
      const connections = await checkResponse.json();
      if (connections && connections.length > 0) {
        return NextResponse.json({
          message: "User already has connections",
          connections
        });
      }
    }

    // Get default WordPress config from environment (server-side only)
    // Users never access WordPress directly - all requests proxied through Next.js API
    const defaultConnection = {
      name: process.env.DEFAULT_WP_NAME || "Local WordPress",
      wp_url: process.env.DEFAULT_WP_URL || "http://localhost:8080",
      wp_graphql_endpoint: process.env.DEFAULT_WP_GRAPHQL_ENDPOINT || "http://localhost:8080/graphql",
      wp_user: process.env.DEFAULT_WP_USER || "admin",
      wp_app_password: process.env.DEFAULT_WP_APP_PASSWORD || "",
    };

    // Validate we have an app password
    if (!defaultConnection.wp_app_password) {
      return NextResponse.json(
        {
          error: "No default WordPress app password configured",
          needsSetup: true
        },
        { status: 400 }
      );
    }

    // Create default connection
    const response = await fetch(`${MCP_SERVER_URL}/connections`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      body: JSON.stringify(defaultConnection),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        {
          error: error.message || "Failed to create default connection",
          needsSetup: true
        },
        { status: response.status }
      );
    }

    const connection = await response.json();
    return NextResponse.json({
      success: true,
      connection,
      message: "Default WordPress connection created"
    });
  } catch (error) {
    console.error("Setup default connection error:", error);
    return NextResponse.json(
      {
        error: "Failed to setup default connection",
        needsSetup: true
      },
      { status: 500 }
    );
  }
}
