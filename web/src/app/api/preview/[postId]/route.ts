import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ postId: string }> }
) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const { postId } = await params;
    const post_id = parseInt(postId, 10);

    if (isNaN(post_id)) {
      return NextResponse.json(
        { error: "Invalid post ID" },
        { status: 400 }
      );
    }

    const result = await callMCPTool(
      "get_preview_html",
      { post_id },
      authHeaders
    );

    if (result && typeof result === "object" && "error" in result) {
      return NextResponse.json(
        { error: result.error },
        { status: 500 }
      );
    }

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
