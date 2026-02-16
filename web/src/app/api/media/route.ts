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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { file_url, title, alt_text } = body;

    if (!file_url) {
      return NextResponse.json(
        { error: "file_url is required" },
        { status: 400 }
      );
    }

    const result = await callMCPTool("upload_media", {
      file_url,
      title: title || "",
      alt_text: alt_text || "",
    });

    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 500 });
    }

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
