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
