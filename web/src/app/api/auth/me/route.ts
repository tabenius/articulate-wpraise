import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: 401 }
      );
    }

    // Call MCP server to get user from session
    const response = await fetch(`${MCP_SERVER_URL}/me`, {
      method: "GET",
      headers: {
        "X-Session-ID": sessionCookie.value,
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Session invalid" },
        { status: 401 }
      );
    }

    const user = await response.json();
    return NextResponse.json({ user });
  } catch (error) {
    console.error("Auth check error:", error);
    return NextResponse.json(
      { error: "Auth check failed" },
      { status: 500 }
    );
  }
}
