import { NextResponse } from "next/server";
import type { ApiErrorPayload } from "@/lib/api-contract";

export function apiError(status: number, error: ApiErrorPayload) {
  return NextResponse.json({ error }, { status });
}

export function apiOk<T>(data: T, requestId: string, meta: Record<string, unknown> = {}) {
  return NextResponse.json({ data, meta: { requestId, ...meta } });
}
