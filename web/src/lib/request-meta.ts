import { NextRequest } from "next/server";

export function createRequestId(): string {
  return crypto.randomUUID();
}

export function getOrCreateRequestId(request: NextRequest): string {
  return request.headers.get("x-request-id") || createRequestId();
}

export function getOrCreateIdempotencyKey(request: NextRequest): string {
  return request.headers.get("idempotency-key") || crypto.randomUUID();
}
