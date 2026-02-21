import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";

export async function GET(request: NextRequest) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const searchParams = request.nextUrl.searchParams;
    const status = searchParams.get("status") || "any";
    const search = searchParams.get("search") || undefined;
    const perPage = parseInt(searchParams.get("per_page") || "20", 10);

    const result = await callMCPTool(
      "get_posts",
      {
        status,
        per_page: perPage,
        ...(search ? { search } : {}),
      },
      authHeaders
    );

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const body = await request.json();
    const { title, content, status, type } = body;

    // Validate required fields
    if (!title || typeof title !== "string") {
      return NextResponse.json({ error: "Title is required and must be a string" }, { status: 400 });
    }

    // Validate optional fields
    if (content && typeof content !== "string") {
      return NextResponse.json({ error: "Content must be a string" }, { status: 400 });
    }

    // Validate status enum
    const validStatuses = ["draft", "publish", "pending", "private"];
    const postStatus = status || "draft";
    if (!validStatuses.includes(postStatus)) {
      return NextResponse.json(
        { error: `Invalid status. Must be one of: ${validStatuses.join(", ")}` },
        { status: 400 }
      );
    }

    // Validate type enum
    const validTypes = ["post", "page"];
    const postType = type || "post";
    if (!validTypes.includes(postType)) {
      return NextResponse.json(
        { error: `Invalid type. Must be one of: ${validTypes.join(", ")}` },
        { status: 400 }
      );
    }

    const result = await callMCPTool(
      "create_post",
      {
        title: title.trim(),
        content: content?.trim() || "",
        status: postStatus,
        post_type: postType,
      },
      authHeaders
    );

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
