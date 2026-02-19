import { NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

// List all menus
export async function GET() {
  try {
    const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "list_menus",
          arguments: {},
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`MCP server error: ${response.statusText}`);
    }

    const data = await response.json();
    const result = data.result?.content?.[0]?.text
      ? JSON.parse(data.result.content[0].text)
      : data.result;

    return NextResponse.json(result);
  } catch (error) {
    console.error("Failed to list menus:", error);
    return NextResponse.json(
      { error: "Failed to list menus" },
      { status: 500 }
    );
  }
}
