import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const postId = searchParams.get("postId");
  const limit = searchParams.get("limit") || "50";

  if (!postId) {
    return NextResponse.json(
      { error: "Post ID required" },
      { status: 400 }
    );
  }

  try {
    const response = await fetch("http://mcp-server:8000/call-tool", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "get_post_revisions",
        arguments: {
          post_id: parseInt(postId),
          limit: parseInt(limit),
        },
      }),
    });

    if (!response.ok) {
      throw new Error("MCP server error");
    }

    const data = await response.json();
    return NextResponse.json(data.content[0].text ? JSON.parse(data.content[0].text) : []);
  } catch (error) {
    console.error("Failed to fetch revisions:", error);
    return NextResponse.json(
      { error: "Failed to fetch revisions" },
      { status: 500 }
    );
  }
}
