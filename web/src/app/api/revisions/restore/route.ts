import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { postId, revisionId } = await request.json();

    if (!postId || !revisionId) {
      return NextResponse.json(
        { error: "Post ID and revision ID required" },
        { status: 400 }
      );
    }

    const response = await fetch("http://mcp-server:8000/call-tool", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "restore_revision",
        arguments: {
          post_id: postId,
          revision_id: revisionId,
        },
      }),
    });

    if (!response.ok) {
      throw new Error("MCP server error");
    }

    const data = await response.json();
    return NextResponse.json(data.content[0].text ? JSON.parse(data.content[0].text) : {});
  } catch (error) {
    console.error("Failed to restore revision:", error);
    return NextResponse.json(
      { error: "Failed to restore revision" },
      { status: 500 }
    );
  }
}
