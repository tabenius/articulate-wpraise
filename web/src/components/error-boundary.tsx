"use client";

import React from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console in development
    console.error("Error boundary caught error:", error, errorInfo);

    // In production, you could send this to an error tracking service
    if (process.env.NODE_ENV === "production") {
      // Example: logErrorToService(error, errorInfo);
    }
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={this.state.error} reset={this.reset} />;
      }

      // Default fallback UI
      return <DefaultErrorFallback error={this.state.error} reset={this.reset} />;
    }

    return this.props.children;
  }
}

function DefaultErrorFallback({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex items-center justify-center min-h-screen p-4 bg-background">
      <div className="max-w-md w-full">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Something went wrong</AlertTitle>
          <AlertDescription className="mt-2 space-y-2">
            <p className="text-sm">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            {process.env.NODE_ENV === "development" && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-medium">
                  Error details (development only)
                </summary>
                <pre className="mt-2 text-xs overflow-auto p-2 bg-muted rounded">
                  {error.message}
                  {"\n\n"}
                  {error.stack}
                </pre>
              </details>
            )}
          </AlertDescription>
        </Alert>
        <div className="mt-4 flex gap-2">
          <Button onClick={reset} className="flex-1">
            Try again
          </Button>
          <Button
            onClick={() => window.location.reload()}
            variant="outline"
            className="flex-1"
          >
            Refresh page
          </Button>
        </div>
      </div>
    </div>
  );
}
