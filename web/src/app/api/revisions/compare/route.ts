import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { postId, revisionId1, revisionId2 } = await request.json();

    if (!postId || !revisionId1 || !revisionId2) {
      return NextResponse.json(
        { error: "Post ID and revision IDs required" },
        { status: 400 }
      );
    }

    const response = await fetch("http://mcp-server:8000/call-tool", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "compare_revisions",
        arguments: {
          post_id: postId,
          revision_id_1: revisionId1,
          revision_id_2: revisionId2,
        },
      }),
    });

    if (!response.ok) {
      throw new Error("MCP server error");
    }

    const data = await response.json();
    return NextResponse.json(data.content[0].text ? JSON.parse(data.content[0].text) : {});
  } catch (error) {
    console.error("Failed to compare revisions:", error);
    return NextResponse.json(
      { error: "Failed to compare revisions" },
      { status: 500 }
    );
  }
}
