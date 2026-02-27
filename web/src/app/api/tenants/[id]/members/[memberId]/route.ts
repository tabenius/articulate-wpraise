import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; memberId: string }> }
) {
  try {
    const { id, memberId } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/tenants/${id}/members/${memberId}`, {
      method: "PUT",
      headers: {
        "X-Session-ID": sessionCookie.value,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Update tenant member error:", error);
    return NextResponse.json({ error: "Failed to update member" }, { status: 500 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; memberId: string }> }
) {
  try {
    const { id, memberId } = await params;
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const response = await fetch(`${MCP_SERVER_URL}/tenants/${id}/members/${memberId}`, {
      method: "DELETE",
      headers: { "X-Session-ID": sessionCookie.value },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Remove tenant member error:", error);
    return NextResponse.json({ error: "Failed to remove member" }, { status: 500 });
  }
}
