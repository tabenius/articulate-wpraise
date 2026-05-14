export type ApiErrorCode =
  | "AUTH_REQUIRED"
  | "VALIDATION_ERROR"
  | "UPSTREAM_UNAVAILABLE"
  | "UPSTREAM_REJECTED"
  | "CAPABILITY_MISSING"
  | "WRITE_GUARD_FAILED"
  | "INTERNAL_ERROR";

export interface ApiErrorPayload {
  code: ApiErrorCode;
  message: string;
  remediation?: string;
  requestId?: string;
  retryable?: boolean;
  details?: unknown;
}

export interface ApiSuccessMeta {
  requestId: string;
  degraded?: boolean;
  source?: "live" | "cache";
}

export function getErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "Unknown error";
  const record = payload as Record<string, unknown>;
  const err = record.error as Record<string, unknown> | undefined;
  if (err && typeof err.message === "string") return err.message;
  if (typeof record.error === "string") return record.error;
  return "Unknown error";
}
