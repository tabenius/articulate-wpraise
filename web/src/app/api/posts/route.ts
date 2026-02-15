import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const status = searchParams.get("status") || "publish";
    const search = searchParams.get("search") || undefined;
    const perPage = parseInt(searchParams.get("per_page") || "20", 10);

    const result = await callMCPTool("get_posts", {
      status,
      per_page: perPage,
      ...(search ? { search } : {}),
    });

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { title, content, status } = body;

    if (!title) {
      return NextResponse.json({ error: "Title is required" }, { status: 400 });
    }

    const result = await callMCPTool("create_post", {
      title,
      content: content || "",
      status: status || "draft",
    });

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
