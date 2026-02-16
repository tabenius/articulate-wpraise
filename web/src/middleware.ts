import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Define public routes that don't require authentication
const PUBLIC_ROUTES = ["/login", "/api/auth/login"];

// Define API routes that should have token passed through
const API_ROUTES = ["/api/posts", "/api/pages", "/api/blocks", "/api/media", "/api/taxonomies"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for authentication token
  const authHeader = request.headers.get("authorization");
  let token: string | null = null;

  // Get token from Authorization header
  if (authHeader && authHeader.startsWith("Bearer ")) {
    token = authHeader.substring(7);
  }

  // Try to get token from stored state (for client-side navigation)
  // Note: This requires the auth store to be initialized on the client
  if (!token && typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("wp-ai-auth-storage");
      if (stored) {
        const parsed = JSON.parse(stored);
        token = parsed.state?.token || null;
      }
    } catch (e) {
      // Ignore errors
    }
  }

  // For API routes, add token header if available
  if (API_ROUTES.some((route) => pathname.startsWith(route))) {
    const headers = new Headers(request.headers);

    if (token) {
      headers.set("X-WP-AI-Token", token);
    }

    return NextResponse.next({
      request: {
        headers,
      },
    });
  }

  // For protected pages, redirect to login if no token
  // Note: This is a basic check. Full verification happens on the server
  if (!pathname.startsWith("/api") && !token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
