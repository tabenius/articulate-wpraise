import { NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_URL = process.env.MCP_SERVER_URL || "http://mcp-server:8000";

export async function GET() {
  try {
    const headers = await getSessionHeaders();
    if (!headers) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const res = await fetch(`${MCP_URL}/capabilities`, {
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Capabilities fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch capabilities" },
      { status: 500 }
    );
  }
}
