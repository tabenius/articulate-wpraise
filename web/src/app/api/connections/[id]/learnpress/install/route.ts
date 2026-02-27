import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");

    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const body = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/connections/${id}/learnpress/install`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      return NextResponse.json({ error: data.error || "Failed to install LearnPress", details: data }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Install LearnPress error:", error);
    return NextResponse.json({ error: "Failed to install LearnPress" }, { status: 500 });
  }
}
