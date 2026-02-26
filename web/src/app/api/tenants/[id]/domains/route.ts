import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(
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

    const body = await request.json();
    if (!body.external_domain || !body.target_view) {
      return NextResponse.json({ error: "external_domain and target_view are required" }, { status: 400 });
    }

    const response = await fetch(`${MCP_SERVER_URL}/tenants/${id}/domains`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
      },
      body: JSON.stringify({
        external_domain: body.external_domain,
        target_view: body.target_view,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error("Add domain error:", error);
    return NextResponse.json({ error: "Failed to add domain" }, { status: 500 });
  }
}
