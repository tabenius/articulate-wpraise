import React from "react";
import { toast } from "@/hooks/use-toast";

interface ErrorAction {
  label: string;
  onClick: () => void;
}

export function showActionableError(
  title: string,
  description: string,
  actions?: ErrorAction[]
) {
  toast({
    variant: "destructive",
    title,
    description: (
      <div className="space-y-3">
        <p>{description}</p>
        {actions && actions.length > 0 && (
          <div className="flex gap-2 mt-2">
            {actions.map((action, index) => (
              <button
                key={index}
                onClick={action.onClick}
                className="px-3 py-1 text-sm bg-destructive-foreground text-destructive rounded hover:opacity-90 transition-opacity"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    ),
  });
}

export function handleConnectionError(error: unknown, retryFn?: () => void) {
  const message = error instanceof Error ? error.message : "Connection failed";

  showActionableError(
    "Connection Error",
    message,
    [
      ...(retryFn ? [{ label: "Retry", onClick: retryFn }] : []),
      { label: "Check Connections", onClick: () => window.location.href = "/connections" },
    ]
  );
}

export function handleAuthError(error: unknown) {
  showActionableError(
    "Authentication Error",
    "Your session may have expired",
    [
      { label: "Sign In", onClick: () => window.location.href = "/auth" },
    ]
  );
}

export function handleSaveError(error: unknown, retryFn?: () => void) {
  const message = error instanceof Error ? error.message : "Failed to save changes";

  showActionableError(
    "Save Error",
    message,
    retryFn ? [{ label: "Retry", onClick: retryFn }] : undefined
  );
}
