import { cookies } from "next/headers";
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
    // Note: We'll need to add a /me endpoint to MCP server
    // For now, return a simple response
    return NextResponse.json(
      { authenticated: true, session_id: sessionCookie.value },
      { status: 200 }
    );
  } catch (error) {
    console.error("Auth check error:", error);
    return NextResponse.json(
      { error: "Auth check failed" },
      { status: 500 }
    );
  }
}
