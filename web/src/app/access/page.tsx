"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

export const dynamic = "force-dynamic";

function AccessContent() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [result, setResult] = useState<{
    valid: boolean;
    product_name?: string;
    content_ids?: number[];
    file_path?: string;
    file_name?: string;
    download_count?: number;
    download_limit?: number | null;
    expires_at?: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const urlToken = searchParams.get("token");
    if (urlToken) {
      validateToken(urlToken);
    }
  }, [searchParams]);

  async function validateToken(t: string) {
    if (!t.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/payments/validate-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: t.trim() }),
      });
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch {
      setError("Failed to validate token");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Access Content</h1>
          <p className="text-muted-foreground mt-2">
            Enter your access token to view purchased content
          </p>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && validateToken(token)}
            placeholder="Paste your access token..."
            className="w-full px-4 py-3 border rounded-lg bg-background text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={() => validateToken(token)}
            disabled={loading || !token.trim()}
            className="w-full py-3 bg-primary text-primary-foreground rounded-lg
                       font-medium disabled:opacity-50"
          >
            {loading ? "Validating..." : "Access Content"}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            {error}
          </div>
        )}

        {result && !result.valid && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            Invalid or expired token. Please check your token and try again.
          </div>
        )}

        {result && result.valid && (
          <div className="p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg space-y-3">
            <h2 className="font-semibold text-green-800 dark:text-green-200">
              Access Granted
            </h2>
            <p className="text-sm text-green-700 dark:text-green-300">
              <strong>{result.product_name}</strong>
            </p>
            {result.content_ids && result.content_ids.length > 0 && (
              <p className="text-sm text-green-600 dark:text-green-400">
                {result.content_ids.length} content item{result.content_ids.length !== 1 ? "s" : ""} available
              </p>
            )}
            {result.download_limit && (
              <p className="text-xs text-green-600 dark:text-green-400">
                Downloads: {result.download_count} / {result.download_limit}
              </p>
            )}
            {result.expires_at && (
              <p className="text-xs text-green-600 dark:text-green-400">
                Expires: {new Date(result.expires_at).toLocaleDateString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center"><p className="text-muted-foreground">Loading...</p></div>}>
      <AccessContent />
    </Suspense>
  );
}
