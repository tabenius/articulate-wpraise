import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
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

    const perPage = parseInt(
      request.nextUrl.searchParams.get("per_page") || "20",
      10
    );

    const result = await callMCPTool("get_media", { per_page: perPage }, authHeaders);
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

    const contentType = request.headers.get("content-type") || "";

    // Handle FormData (file upload)
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("file") as File;
      const title = (formData.get("title") as string) || "";
      const alt_text = (formData.get("alt_text") as string) || "";

      if (!file) {
        return NextResponse.json(
          { error: "file is required" },
          { status: 400 }
        );
      }

      // Convert file to base64
      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);
      const base64 = buffer.toString("base64");

      // Create a data URL
      const dataUrl = `data:${file.type};base64,${base64}`;

      // Upload via MCP using the data URL
      const result = await callMCPTool("upload_media", {
        file_url: dataUrl,
        title,
        alt_text,
      }, authHeaders) as { error?: string; id?: number; url?: string };

      if (result.error) {
        return NextResponse.json({ error: result.error }, { status: 500 });
      }

      return NextResponse.json(result);
    }

    // Handle JSON (URL upload)
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
    }, authHeaders) as { error?: string; id?: number; url?: string };

    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 500 });
    }

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
