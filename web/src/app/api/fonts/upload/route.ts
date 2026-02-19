import { NextRequest, NextResponse } from "next/server";
import { writeFile, unlink } from "fs/promises";
import { join } from "path";
import { callMCPTool } from "@/lib/mcp-client";

// Create temp directory for uploaded files
const TEMP_DIR = join(process.cwd(), "public", "temp");
const PUBLIC_BASE_URL = process.env.NEXT_PUBLIC_URL || "http://localhost:3000";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    const fontFamily = formData.get("font_family") as string;
    const fontWeight = formData.get("font_weight") as string;
    const fontStyle = formData.get("font_style") as string;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    // Validate file type
    const validExtensions = [".woff2", ".woff", ".ttf", ".otf", ".eot"];
    const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
    if (!validExtensions.includes(fileExt)) {
      return NextResponse.json(
        { error: "Invalid font file type" },
        { status: 400 }
      );
    }

    // Save file to temp directory
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Ensure temp directory exists
    const fs = require("fs");
    if (!fs.existsSync(TEMP_DIR)) {
      fs.mkdirSync(TEMP_DIR, { recursive: true });
    }

    // Generate unique filename
    const timestamp = Date.now();
    const filename = `${timestamp}-${file.name}`;
    const filepath = join(TEMP_DIR, filename);

    // Write file to disk
    await writeFile(filepath, buffer);

    // Generate public URL for the temp file
    const fileUrl = `${PUBLIC_BASE_URL}/temp/${filename}`;

    try {
      // Call MCP tool to upload font to WordPress
      const result = await callMCPTool("upload_font", {
        file_url: fileUrl,
        font_family: fontFamily || "",
        font_weight: fontWeight || "400",
        font_style: fontStyle || "normal",
      }) as { error?: string; id?: string; family?: string };

      // Clean up temp file after upload
      try {
        await unlink(filepath);
      } catch (unlinkError) {
        console.error("Failed to delete temp file:", unlinkError);
      }

      if (result.error) {
        return NextResponse.json({ error: result.error }, { status: 500 });
      }

      return NextResponse.json(result);
    } catch (mcpError) {
      // Clean up temp file on error
      try {
        await unlink(filepath);
      } catch (unlinkError) {
        console.error("Failed to delete temp file:", unlinkError);
      }

      throw mcpError;
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
