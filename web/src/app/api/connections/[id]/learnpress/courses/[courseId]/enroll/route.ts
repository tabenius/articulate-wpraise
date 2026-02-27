import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; courseId: string }> }
) {
  try {
    const { id, courseId } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const response = await fetch(
      `${MCP_SERVER_URL}/connections/${id}/learnpress/courses/${courseId}/enroll`,
      {
        method: "POST",
        headers: {
          "X-Session-ID": sessionCookie.value,
          "Content-Type": "application/json",
        },
      }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("LP enroll error:", error);
    return NextResponse.json({ error: "Failed to enroll" }, { status: 500 });
  }
}
