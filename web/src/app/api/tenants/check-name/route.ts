import { NextRequest, NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const name = request.nextUrl.searchParams.get("name");
    if (!name) {
      return NextResponse.json({ error: "name parameter required" }, { status: 400 });
    }

    const res = await fetch(
      `${MCP_SERVER_URL}/tenants/check-name?name=${encodeURIComponent(name)}`,
      { headers: authHeaders }
    );
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
