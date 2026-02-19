import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";

export async function GET(request: NextRequest) {
  try {
    const result = await callMCPTool("list_fonts", {});
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
