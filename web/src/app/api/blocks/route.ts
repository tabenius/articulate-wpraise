import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { callMCPTool } from "@/lib/mcp-client";

export async function GET(request: NextRequest) {
  try {
    const postId = parseInt(
      request.nextUrl.searchParams.get("postId") || "0",
      10
    );
    if (!postId) {
      return NextResponse.json(
        { error: "postId is required" },
        { status: 400 }
      );
    }

    const result = await callMCPTool("get_blocks", { post_id: postId });
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { postId, blocks } = body;

    if (!postId || !blocks) {
      return NextResponse.json(
        { error: "postId and blocks are required" },
        { status: 400 }
      );
    }

    const result = await callMCPTool("update_blocks", {
      post_id: postId,
      blocks,
    });

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
