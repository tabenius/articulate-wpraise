import { NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${MCP_SERVER_URL}/payments/products`);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Products list error:", error);
    return NextResponse.json({ error: "Failed to list products" }, { status: 500 });
  }
}
