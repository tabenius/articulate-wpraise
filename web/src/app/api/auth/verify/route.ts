import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    // Get token from Authorization header
    const authHeader = request.headers.get("authorization");
    let token = null;

    if (authHeader && authHeader.startsWith("Bearer ")) {
      token = authHeader.substring(7);
    }

    if (!token) {
      return NextResponse.json(
        { error: "No token provided", valid: false },
        { status: 401 }
      );
    }

    // Get WordPress URL from environment
    const wpUrl = process.env.WP_URL || "http://wordpress:80";

    // Call WordPress JWT verify endpoint
    const response = await fetch(`${wpUrl}/wp-json/wp-ai/v1/auth/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Invalid token", valid: false },
        { status: 401 }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      valid: data.valid,
      user: data.user,
    });
  } catch (error) {
    console.error("Verify error:", error);
    return NextResponse.json(
      { error: "Token verification failed", valid: false },
      { status: 500 }
    );
  }
}
