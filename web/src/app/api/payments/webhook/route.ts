import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const sig = request.headers.get("stripe-signature") || "";

    const response = await fetch(`${MCP_SERVER_URL}/payments/webhook`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "stripe-signature": sig,
      },
      body,
    });

    return new NextResponse(null, { status: response.status });
  } catch (error) {
    console.error("Webhook relay error:", error);
    return new NextResponse(null, { status: 500 });
  }
}
