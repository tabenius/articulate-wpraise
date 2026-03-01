import { NextRequest, NextResponse } from "next/server";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ api_key: string }> }
) {
  try {
    const { api_key } = await params;
    const body = await request.text();

    const response = await fetch(
      `http://mcp-server:8000/mcp/c/${api_key}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body,
      }
    );

    const data = await response.text();
    return new NextResponse(data, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("MCP API key proxy error:", error);
    return NextResponse.json(
      { error: "MCP request failed" },
      { status: 500 }
    );
  }
}
