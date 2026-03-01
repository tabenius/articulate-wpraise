"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

export default function PurchaseSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState<"loading" | "completed" | "pending">("loading");
  const [accessToken, setAccessToken] = useState("");
  const [productName, setProductName] = useState("");

  useEffect(() => {
    if (!sessionId) return;

    async function checkSession() {
      try {
        const response = await fetch(`/api/payments/session/${sessionId}`);
        const data = await response.json();

        if (data.status === "completed") {
          setStatus("completed");
          setAccessToken(data.access_token);
          setProductName(data.product_name);
        } else {
          setStatus("pending");
          setTimeout(checkSession, 3000);
        }
      } catch {
        setStatus("pending");
      }
    }

    checkSession();
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 text-center">
        {status === "loading" && (
          <p className="text-muted-foreground">Processing your purchase...</p>
        )}

        {status === "pending" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Payment Received</h1>
            <p className="text-muted-foreground">
              Your access is being set up. Check your email shortly for your
              access token.
            </p>
          </div>
        )}

        {status === "completed" && (
          <div className="space-y-4">
            <div className="text-4xl">&#10003;</div>
            <h1 className="text-2xl font-bold">Purchase Complete!</h1>
            <p className="text-muted-foreground">
              You now have access to <strong>{productName}</strong>.
            </p>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-2">Your access token:</p>
              <code className="text-sm font-mono break-all">{accessToken}</code>
            </div>
            <p className="text-xs text-muted-foreground">
              This token has also been emailed to you.
            </p>
            <a
              href={`/access?token=${accessToken}`}
              className="inline-block py-3 px-6 bg-primary text-primary-foreground
                         rounded-lg font-medium"
            >
              Access Your Content
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
