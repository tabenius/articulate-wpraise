import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { callMCPTool } from "@/lib/mcp-client";

export async function GET(request: NextRequest) {
  try {
    const type = request.nextUrl.searchParams.get("type") || "both";
    const perPage = parseInt(
      request.nextUrl.searchParams.get("per_page") || "100",
      10
    );

    if (type === "categories") {
      const result = await callMCPTool("get_categories", { per_page: perPage });
      return NextResponse.json({ categories: result });
    } else if (type === "tags") {
      const result = await callMCPTool("get_tags", { per_page: perPage });
      return NextResponse.json({ tags: result });
    } else {
      // Get both
      const [categories, tags] = await Promise.all([
        callMCPTool("get_categories", { per_page: perPage }),
        callMCPTool("get_tags", { per_page: perPage }),
      ]);
      return NextResponse.json({ categories, tags });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { type, name, description } = body;

    if (!type || !name) {
      return NextResponse.json(
        { error: "type and name are required" },
        { status: 400 }
      );
    }

    if (type === "category") {
      const result = await callMCPTool("create_category", {
        name,
        description: description || "",
      });
      return NextResponse.json(result);
    } else if (type === "tag") {
      const result = await callMCPTool("create_tag", {
        name,
        description: description || "",
      });
      return NextResponse.json(result);
    } else {
      return NextResponse.json(
        { error: "type must be 'category' or 'tag'" },
        { status: 400 }
      );
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
