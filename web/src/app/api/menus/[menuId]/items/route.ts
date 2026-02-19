import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

// Get menu items
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ menuId: string }> }
) {
  try {
    const { menuId: menuIdStr } = await params;
    const menuId = parseInt(menuIdStr);

    const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "get_menu_items",
          arguments: { menu_id: menuId },
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
    console.error("Failed to get menu items:", error);
    return NextResponse.json(
      { error: "Failed to get menu items" },
      { status: 500 }
    );
  }
}

// Add page to menu
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ menuId: string }> }
) {
  try {
    const { menuId: menuIdStr } = await params;
    const menuId = parseInt(menuIdStr);
    const { pageId, label } = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "add_page_to_menu",
          arguments: {
            page_id: pageId,
            menu_id: menuId,
            label: label || null,
          },
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
    console.error("Failed to add page to menu:", error);
    return NextResponse.json(
      { error: "Failed to add page to menu" },
      { status: 500 }
    );
  }
}

// Remove page from menu
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ menuId: string }> }
) {
  try {
    const { menuId: menuIdStr } = await params;
    const menuId = parseInt(menuIdStr);
    const { searchParams } = new URL(request.url);
    const pageId = parseInt(searchParams.get("pageId") || "0");

    const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "remove_page_from_menu",
          arguments: {
            page_id: pageId,
            menu_id: menuId,
          },
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
    console.error("Failed to remove page from menu:", error);
    return NextResponse.json(
      { error: "Failed to remove page from menu" },
      { status: 500 }
    );
  }
}
