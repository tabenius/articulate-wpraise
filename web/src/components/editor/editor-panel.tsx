"use client";

import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { BlockEditor } from "./block-editor";
import { BlockToolbar } from "./block-toolbar";
import { PreviewMode } from "./preview-mode";
import { DesignSystemPanel } from "./design-system-panel";
import { RevisionTimeline } from "./revision-timeline";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { Undo2, Redo2 } from "lucide-react";

export function EditorPanel() {
  const [isPreview, setIsPreview] = useState(false);
  const currentPost = usePostStore((s) => s.currentPost);
  const blocks = useEditorStore((s) => s.blocks);
  const blockCount = blocks.length;
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const canUndo = useEditorStore((s) => s.canUndo());
  const canRedo = useEditorStore((s) => s.canRedo());

  // Calculate word count and reading time
  const wordCount = blocks.reduce((count, block) => {
    const content = block.attributes.content as string || "";
    const text = content.replace(/<[^>]*>/g, ""); // Strip HTML tags
    const words = text.trim().split(/\s+/).filter(Boolean);
    return count + words.length;
  }, 0);

  const readingTime = Math.max(1, Math.ceil(wordCount / 200)); // 200 words per minute

  if (isPreview) {
    return (
      <PreviewMode
        isPreview={isPreview}
        onTogglePreview={() => setIsPreview(false)}
      />
    );
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Editor toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <BlockToolbar />
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={undo}
              disabled={!canUndo}
              title="Undo (Cmd+Z)"
              className="h-8 w-8 p-0"
            >
              <Undo2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={redo}
              disabled={!canRedo}
              title="Redo (Cmd+Shift+Z)"
              className="h-8 w-8 p-0"
            >
              <Redo2 className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{blockCount} block{blockCount !== 1 ? "s" : ""}</span>
            {wordCount > 0 && (
              <>
                <span>•</span>
                <span>{wordCount} word{wordCount !== 1 ? "s" : ""}</span>
                <span>•</span>
                <span>{readingTime} min read</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DesignSystemPanel />
          <RevisionTimeline />
          <PreviewMode
            isPreview={false}
            onTogglePreview={() => setIsPreview(true)}
          />
          {currentPost && (
            <span className="text-xs text-muted-foreground truncate max-w-[200px]">
              {currentPost.title}
            </span>
          )}
        </div>
      </div>

      {/* Editor content */}
      <ScrollArea className="flex-1">
        <BlockEditor />
      </ScrollArea>
    </div>
  );
}
