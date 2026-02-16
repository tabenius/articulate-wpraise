import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    // Get token from Authorization header
    const authHeader = request.headers.get("authorization");
    let token = null;

    if (authHeader && authHeader.startsWith("Bearer ")) {
      token = authHeader.substring(7);
    }

    if (token) {
      // Get WordPress URL from environment
      const wpUrl = process.env.WP_URL || "http://wordpress:80";

      // Call WordPress logout endpoint (optional, mostly for logging)
      await fetch(`${wpUrl}/wp-json/wp-ai/v1/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
    }

    // Return success (logout is mainly client-side for JWT)
    return NextResponse.json({
      success: true,
      message: "Logged out successfully",
    });
  } catch (error) {
    console.error("Logout error:", error);
    // Return success anyway since JWT logout is stateless
    return NextResponse.json({
      success: true,
      message: "Logged out successfully",
    });
  }
}
