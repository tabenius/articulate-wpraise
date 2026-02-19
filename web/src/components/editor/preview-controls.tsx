"use client";

import { Monitor, Tablet, Smartphone, RefreshCw, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePreviewStore } from "@/stores/preview-store";
import { usePostStore } from "@/stores/post-store";
import { useState } from "react";

export function PreviewControls() {
  const { viewportSize, setViewportSize, isLoading } = usePreviewStore();
  const currentPost = usePostStore((s) => s.currentPost);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (!currentPost) return;

    setIsRefreshing(true);
    // Force re-fetch by clearing and re-setting
    const { setLoading, setHtml } = usePreviewStore.getState();
    setLoading(true);

    try {
      const response = await fetch(`/api/preview/${currentPost.id}`);
      const data = await response.json();
      if (data.success && data.html) {
        setHtml(data.html);
      }
    } catch (error) {
      console.error("Manual refresh failed:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleOpenInWordPress = () => {
    if (!currentPost) return;
    // Open in WordPress frontend - use Caddy proxy in production, direct access in dev
    const wpUrl = process.env.NEXT_PUBLIC_WP_URL ||
                  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:4555` : "");
    window.open(`${wpUrl}/?p=${currentPost.id}`, "_blank", "noopener,noreferrer");
  };

  const viewportButtons = [
    {
      size: "desktop" as const,
      icon: Monitor,
      label: "Desktop",
      tooltip: "Desktop view (full width)",
    },
    {
      size: "tablet" as const,
      icon: Tablet,
      label: "Tablet",
      tooltip: "Tablet view (768px)",
    },
    {
      size: "mobile" as const,
      icon: Smartphone,
      label: "Mobile",
      tooltip: "Mobile view (375px)",
    },
  ];

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b bg-background">
      {/* Viewport size toggles */}
      <div className="flex items-center gap-1 mr-2">
        {viewportButtons.map(({ size, icon: Icon, label, tooltip }) => (
          <Button
            key={size}
            variant={viewportSize === size ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewportSize(size)}
            title={tooltip}
            className="gap-1.5"
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </Button>
        ))}
      </div>

      <div className="h-6 w-px bg-border" />

      {/* Refresh button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={handleRefresh}
        disabled={isLoading || isRefreshing || !currentPost}
        title="Refresh preview"
        className="gap-1.5"
      >
        <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
        <span className="hidden sm:inline">Refresh</span>
      </Button>

      {/* Open in WordPress */}
      <Button
        variant="ghost"
        size="sm"
        onClick={handleOpenInWordPress}
        disabled={!currentPost}
        title="Open in WordPress"
        className="gap-1.5"
      >
        <ExternalLink className="h-4 w-4" />
        <span className="hidden sm:inline">Open in WP</span>
      </Button>

      {/* Loading indicator */}
      {isLoading && (
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <span>Updating preview...</span>
        </div>
      )}
    </div>
  );
}
