import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Define public routes that don't require authentication
const PUBLIC_ROUTES = [
  "/auth",
  "/api/auth/login",
  "/api/auth/register",
  "/api/auth/me",
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for session cookie (HTTP-only)
  const sessionCookie = request.cookies.get("session");

  // For protected pages, redirect to auth if no session
  if (!pathname.startsWith("/api") && !sessionCookie) {
    const url = request.nextUrl.clone();
    url.pathname = "/auth";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  // For API routes, verify session exists
  if (pathname.startsWith("/api") && !PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    if (!sessionCookie) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }
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
