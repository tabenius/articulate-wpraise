import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json(
        { error: "Username and password are required" },
        { status: 400 }
      );
    }

    // Get WordPress URL from environment
    const wpUrl = process.env.WP_URL || "http://wordpress:80";

    // Call WordPress JWT login endpoint
    const response = await fetch(`${wpUrl}/wp-json/wp-ai/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.message || "Login failed" },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Return the token and user data
    return NextResponse.json({
      success: true,
      token: data.token,
      user: data.user,
      expiresAt: data.expiresAt,
    });
  } catch (error) {
    console.error("Login error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Login failed" },
      { status: 500 }
    );
  }
}
