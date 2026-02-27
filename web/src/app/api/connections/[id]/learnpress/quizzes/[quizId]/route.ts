import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; quizId: string }> }
) {
  try {
    const { id, quizId } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const response = await fetch(
      `${MCP_SERVER_URL}/connections/${id}/learnpress/quizzes/${quizId}`,
      { headers: { "X-Session-ID": sessionCookie.value } }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("LP get quiz error:", error);
    return NextResponse.json({ error: "Failed to get quiz" }, { status: 500 });
  }
}
