import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

// Get front page settings
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
          name: "get_front_page_settings",
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
    console.error("Failed to get front page settings:", error);
    return NextResponse.json(
      { error: "Failed to get front page settings" },
      { status: 500 }
    );
  }
}

// Set or unset front page
export async function POST(request: NextRequest) {
  try {
    const { pageId } = await request.json();

    const toolName = pageId ? "set_front_page" : "unset_front_page";
    const args = pageId ? { page_id: pageId } : {};

    const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: toolName,
          arguments: args,
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
    console.error("Failed to update front page:", error);
    return NextResponse.json(
      { error: "Failed to update front page" },
      { status: 500 }
    );
  }
}
