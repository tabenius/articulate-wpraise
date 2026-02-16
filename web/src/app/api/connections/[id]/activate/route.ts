import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    // Get session ID from cookie
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    // Call MCP server to activate connection
    const response = await fetch(
      `http://mcp-server:8000/connections/${id}/activate`,
      {
        method: "POST",
        headers: {
          "X-Session-ID": sessionCookie.value,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.message || "Failed to activate connection" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Activate connection error:", error);
    return NextResponse.json(
      { error: "Failed to activate connection" },
      { status: 500 }
    );
  }
}
