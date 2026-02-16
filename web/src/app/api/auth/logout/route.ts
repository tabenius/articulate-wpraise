import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json(
        { error: "No session found" },
        { status: 400 }
      );
    }

    // Call MCP server to logout
    const response = await fetch("http://mcp-server:8000/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.message || "Logout failed" },
        { status: response.status }
      );
    }

    // Clear session cookie
    cookieStore.delete("session");

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json(
      { error: "Logout failed" },
      { status: 500 }
    );
  }
}
