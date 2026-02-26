import { NextRequest, NextResponse } from "next/server";
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
import { cookies } from "next/headers";

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json();

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${MCP_SERVER_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || "Login failed", email: data.email },
        { status: response.status }
      );
    }

    const cookieStore = await cookies();

    // Always use secure cookies since we're behind HTTPS proxies (Cloudflare/HAProxy)
    // The connection to Next.js is HTTP but the client connection is HTTPS
    const isProxiedHttps =
      request.headers.get("x-forwarded-proto") === "https" ||
      process.env.NODE_ENV === "production";

    cookieStore.set("session", data.session_id, {
      httpOnly: true,
      secure: isProxiedHttps,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
      path: "/",
    });

    return NextResponse.json({
      user: data.user,
      expires_at: data.expires_at,
    });
  } catch (error) {
    console.error("Login error:", error);
    return NextResponse.json(
      { error: "Login failed" },
      { status: 500 }
    );
  }
}
