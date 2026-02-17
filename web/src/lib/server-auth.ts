/**
 * Server-side authentication helpers for API routes
 */

import { cookies } from "next/headers";

/**
 * Get session headers for MCP server requests
 * @returns Headers object with X-Session-ID or null if not authenticated
 */
export async function getSessionHeaders(): Promise<{ "X-Session-ID": string } | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("session");

  if (!sessionCookie) {
    return null;
  }

  return {
    "X-Session-ID": sessionCookie.value,
  };
}

/**
 * Get session cookie value
 * @returns Session cookie value or null
 */
export async function getSessionCookie(): Promise<string | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("session");
  return sessionCookie?.value || null;
}
