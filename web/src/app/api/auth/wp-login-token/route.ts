import { NextRequest, NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const sessionHeaders = await getSessionHeaders();
    if (!sessionHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { tenant_id } = await request.json();

    if (!tenant_id) {
      return NextResponse.json({ error: "tenant_id required" }, { status: 400 });
    }

    const response = await fetch(`${MCP_SERVER_URL}/auth/wp-login-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...sessionHeaders,
      },
      body: JSON.stringify({ tenant_id }),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("WP login token error:", error);
    return NextResponse.json({ error: "Failed to create login token" }, { status: 500 });
  }
}
