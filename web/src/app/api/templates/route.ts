import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";
import { getSessionHeaders } from "@/lib/server-auth";

export async function GET(request: NextRequest) {
  try {
    const authHeaders = await getSessionHeaders();
    if (!authHeaders) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const result = await callMCPTool("get_templates", {}, authHeaders);

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
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { title, slug, content, template_type } = body;

    if (!title || !slug) {
      return NextResponse.json(
        { error: "Title and slug are required" },
        { status: 400 }
      );
    }

    const result = await callMCPTool(
      "create_template",
      {
        title: title.trim(),
        slug: slug.trim(),
        content: content || "",
      },
      authHeaders
    );

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
