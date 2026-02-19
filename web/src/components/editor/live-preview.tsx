"use client";

import { useEffect, useRef } from "react";
import { usePostStore } from "@/stores/post-store";
import { usePreviewStore } from "@/stores/preview-store";
import { usePreview } from "@/hooks/use-preview";
import { Loader2, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function LivePreview() {
  const currentPost = usePostStore((s) => s.currentPost);
  const { html, isLoading, viewportSize, error } = usePreviewStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Auto-fetch preview when blocks change
  usePreview(currentPost?.id ?? null, true);

  // Update iframe content when HTML changes
  useEffect(() => {
    if (!iframeRef.current || !html) return;

    const iframe = iframeRef.current;
    const doc = iframe.contentDocument || iframe.contentWindow?.document;

    if (doc) {
      doc.open();
      doc.write(html);
      doc.close();
    }
  }, [html]);

  // Viewport width mapping
  const viewportWidths = {
    desktop: "100%",
    tablet: "768px",
    mobile: "375px",
  };

  if (!currentPost) {
    return (
      <div className="flex items-center justify-center h-full bg-muted/20">
        <div className="text-center text-muted-foreground">
          <p className="text-sm">No post selected</p>
          <p className="text-xs mt-1">Create or open a post to see preview</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-muted/10 overflow-hidden">
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading preview...</p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center p-6 z-10">
          <Alert variant="destructive" className="max-w-md">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Viewport container - centers iframe and applies width constraint */}
      <div className="h-full w-full flex items-start justify-center overflow-auto bg-gradient-to-b from-muted/20 to-muted/5">
        <div
          className="transition-all duration-300 ease-in-out h-full"
          style={{
            width: viewportWidths[viewportSize],
            maxWidth: "100%",
          }}
        >
          <iframe
            ref={iframeRef}
            className="w-full h-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts allow-popups"
            title="WordPress Preview"
            style={{
              colorScheme: "light",
            }}
          />
        </div>
      </div>

      {/* Viewport indicator */}
      {viewportSize !== "desktop" && (
        <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur-sm border rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-lg">
          {viewportSize === "tablet" && "📱 Tablet (768px)"}
          {viewportSize === "mobile" && "📱 Mobile (375px)"}
        </div>
      )}
    </div>
  );
}
