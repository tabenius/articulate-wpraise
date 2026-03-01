import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return NextResponse.json({ error: "Invalid post ID" }, { status: 400 });
    }

    const type = request.nextUrl.searchParams.get("type") || "post";
    const tool = type === "page" ? "get_page" : "get_post";
    const result = await callMCPTool(tool, { post_id: postId }, authHeaders);
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return NextResponse.json({ error: "Invalid post ID" }, { status: 400 });
    }

    const body = await request.json();
    const {
      title,
      content,
      status,
      featured_image_id,
      category_ids,
      tag_ids,
      date,
    } = body;

    const result = await callMCPTool("update_post", {
      post_id: postId,
      ...(title !== undefined ? { title } : {}),
      ...(content !== undefined ? { content } : {}),
      ...(status !== undefined ? { status } : {}),
      ...(featured_image_id !== undefined ? { featured_image_id } : {}),
      ...(category_ids !== undefined ? { category_ids } : {}),
      ...(tag_ids !== undefined ? { tag_ids } : {}),
      ...(date !== undefined ? { date } : {}),
    }, authHeaders);

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return NextResponse.json({ error: "Invalid post ID" }, { status: 400 });
    }

    const body = await request.json();
    const {
      title,
      content,
      status,
      featured_image_id,
      category_ids,
      tag_ids,
      date,
    } = body;

    const result = await callMCPTool("update_post", {
      post_id: postId,
      ...(title !== undefined ? { title } : {}),
      ...(content !== undefined ? { content } : {}),
      ...(status !== undefined ? { status } : {}),
      ...(featured_image_id !== undefined ? { featured_image_id } : {}),
      ...(category_ids !== undefined ? { category_ids } : {}),
      ...(tag_ids !== undefined ? { tag_ids } : {}),
      ...(date !== undefined ? { date } : {}),
    }, authHeaders);

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const { id } = await params;
    const postId = parseInt(id, 10);
    if (isNaN(postId)) {
      return NextResponse.json({ error: "Invalid post ID" }, { status: 400 });
    }

    const result = await callMCPTool("delete_post", { post_id: postId }, authHeaders);
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
