"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Monitor, Smartphone, Tablet, Eye, EyeOff } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useEditorStore } from "@/stores/editor-store";
import { BlockRenderer } from "./block-renderer";

type ViewportSize = "desktop" | "tablet" | "mobile";

interface PreviewModeProps {
  isPreview: boolean;
  onTogglePreview: () => void;
}

export function PreviewMode({ isPreview, onTogglePreview }: PreviewModeProps) {
  const [viewport, setViewport] = useState<ViewportSize>("desktop");
  const blocks = useEditorStore((s) => s.blocks);

  const viewportSizes = {
    desktop: "max-w-full",
    tablet: "max-w-2xl",
    mobile: "max-w-sm",
  };

  if (!isPreview) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={onTogglePreview}
        title="Preview"
      >
        <Eye className="h-4 w-4 mr-2" />
        Preview
      </Button>
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Preview Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-1">
          <Button
            variant={viewport === "desktop" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setViewport("desktop")}
            title="Desktop"
          >
            <Monitor className="h-4 w-4" />
          </Button>
          <Button
            variant={viewport === "tablet" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setViewport("tablet")}
            title="Tablet"
          >
            <Tablet className="h-4 w-4" />
          </Button>
          <Button
            variant={viewport === "mobile" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setViewport("mobile")}
            title="Mobile"
          >
            <Smartphone className="h-4 w-4" />
          </Button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onTogglePreview}
        >
          <EyeOff className="h-4 w-4 mr-2" />
          Exit Preview
        </Button>
      </div>

      {/* Preview Content */}
      <ScrollArea className="flex-1">
        <div className="flex justify-center p-8">
          <div
            className={`${viewportSizes[viewport]} w-full bg-background border rounded-lg shadow-lg p-8 transition-all duration-300`}
          >
            {blocks.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <p>No content to preview</p>
              </div>
            ) : (
              <div className="space-y-4 prose prose-slate max-w-none">
                {blocks.map((block) => (
                  <BlockRenderer
                    key={block.clientId}
                    block={block}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
