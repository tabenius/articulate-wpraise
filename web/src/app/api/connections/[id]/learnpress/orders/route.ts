import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${MCP_SERVER_URL}/connections/${id}/learnpress/orders${searchParams ? `?${searchParams}` : ""}`;

    const response = await fetch(url, {
      headers: { "X-Session-ID": sessionCookie.value },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("LP orders error:", error);
    return NextResponse.json({ error: "Failed to list orders" }, { status: 500 });
  }
}
