import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";

export async function GET(request: NextRequest) {
  try {
    const perPage = parseInt(
      request.nextUrl.searchParams.get("per_page") || "20",
      10
    );

    const result = await callMCPTool("get_media", { per_page: perPage });
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
