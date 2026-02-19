import { NextRequest, NextResponse } from "next/server";
import { callMCPTool } from "@/lib/mcp-client";

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: fontId } = await params;

    const result = await callMCPTool("delete_font", {
      font_id: fontId,
    }) as { error?: string; success?: boolean; message?: string };

    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 500 });
    }

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
