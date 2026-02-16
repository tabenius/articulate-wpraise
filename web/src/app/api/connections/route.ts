import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Call MCP server to get connections
    const response = await fetch("http://mcp-server:8000/connections", {
      method: "GET",
      headers: {
        "X-Session-ID": sessionCookie.value,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.message || "Failed to get connections" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Get connections error:", error);
    return NextResponse.json(
      { error: "Failed to get connections" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const { name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password } =
      await request.json();

    // Validate input
    if (!name || !wp_url || !wp_graphql_endpoint || !wp_user || !wp_app_password) {
      return NextResponse.json(
        { error: "All fields are required" },
        { status: 400 }
      );
    }

    // Call MCP server to add connection
    const response = await fetch("http://mcp-server:8000/connections", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
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
      return NextResponse.json(
        { error: error.message || "Failed to add connection" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Add connection error:", error);
    return NextResponse.json(
      { error: "Failed to add connection" },
      { status: 500 }
    );
  }
}
