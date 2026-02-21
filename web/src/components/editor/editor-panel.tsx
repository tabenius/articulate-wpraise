"use client";

import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { BlockEditor } from "./block-editor";
import { BlockToolbar } from "./block-toolbar";
import { PreviewMode } from "./preview-mode";
import { LivePreview } from "./live-preview";
import { PreviewControls } from "./preview-controls";
import { DesignSystemPanel } from "./design-system-panel";
import { RevisionTimeline } from "./revision-timeline";
import { PostSettingsDialog } from "./post-settings-dialog";
import { SplitView } from "@/components/layout/split-view";
import { SEOEditor } from "@/components/seo/seo-editor";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { Undo2, Redo2, Edit3, Columns2, Eye } from "lucide-react";

type ViewMode = "edit" | "split" | "preview";

export function EditorPanel() {
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const currentPost = usePostStore((s) => s.currentPost);
  const blocks = useEditorStore((s) => s.blocks);
  const blockCount = blocks.length;
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const canUndo = useEditorStore((s) => s.canUndo());
  const canRedo = useEditorStore((s) => s.canRedo());

  // Calculate word count and reading time
  const wordCount = blocks.reduce((count, block) => {
    // Validate block structure
    if (!block || !block.attributes) return count;

    // Only count blocks that have text content (paragraph, heading, quote, code, list)
    const content =
      block.attributes.content ||
      block.attributes.value ||
      block.attributes.values;

    // Handle string content
    if (typeof content === "string") {
      const text = content.replace(/<[^>]*>/g, ""); // Strip HTML tags
      const words = text.trim().split(/\s+/).filter(Boolean);
      return count + words.length;
    }

    // Handle array content (for list blocks)
    if (Array.isArray(content)) {
      const text = content.join(" ").replace(/<[^>]*>/g, "");
      const words = text.trim().split(/\s+/).filter(Boolean);
      return count + words.length;
    }

    return count;
  }, 0);

  const readingTime = Math.max(1, Math.ceil(wordCount / 200)); // 200 words per minute

  // Render old preview mode for backward compatibility
  if (viewMode === "preview") {
    return (
      <PreviewMode isPreview={true} onTogglePreview={() => setViewMode("edit")} />
    );
  }

  // Render split view: Editor | Live WordPress Preview
  if (viewMode === "split") {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* View mode toggle toolbar */}
        <ViewModeToolbar viewMode={viewMode} setViewMode={setViewMode} />

        {/* Preview controls */}
        <PreviewControls />

        {/* Split view content */}
        <div className="flex-1">
          <SplitView
            left={
              <div className="h-full flex flex-col">
                {/* Editor toolbar */}
                <EditorToolbar
                  blockCount={blockCount}
                  wordCount={wordCount}
                  readingTime={readingTime}
                  undo={undo}
                  redo={redo}
                  canUndo={canUndo}
                  canRedo={canRedo}
                  currentPost={currentPost}
                />
                {/* Editor content */}
                <ScrollArea className="flex-1">
                  <BlockEditor />

                  {/* SEO Editor */}
                  {currentPost && (
                    <div className="max-w-3xl mx-auto px-12 py-8">
                      <SEOEditor
                        postId={currentPost.id}
                        postTitle={currentPost.title}
                        postExcerpt=""
                      />
                    </div>
                  )}
                </ScrollArea>
              </div>
            }
            right={<LivePreview />}
            defaultSize={50}
            leftId="editor-panel"
            rightId="preview-panel"
          />
        </div>
      </div>
    );
  }

  // Render edit mode (default)
  return (
    <div className="h-full flex flex-col bg-background">
      {/* View mode toggle toolbar */}
      <ViewModeToolbar viewMode={viewMode} setViewMode={setViewMode} />

      {/* Editor toolbar */}
      <EditorToolbar
        blockCount={blockCount}
        wordCount={wordCount}
        readingTime={readingTime}
        undo={undo}
        redo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
        currentPost={currentPost}
      />

      {/* Editor content */}
      <ScrollArea className="flex-1">
        <BlockEditor />

        {/* SEO Editor */}
        {currentPost && (
          <div className="max-w-3xl mx-auto px-12 py-8">
            <SEOEditor
              postId={currentPost.id}
              postTitle={currentPost.title}
              postExcerpt=""
            />
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

// View mode toggle component
function ViewModeToolbar({
  viewMode,
  setViewMode,
}: {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}) {
  const modes: { mode: ViewMode; icon: typeof Edit3; label: string }[] = [
    { mode: "edit", icon: Edit3, label: "Edit" },
    { mode: "split", icon: Columns2, label: "Split" },
    { mode: "preview", icon: Eye, label: "Preview" },
  ];

  return (
    <div className="flex items-center gap-1 px-4 py-2 border-b bg-muted/20">
      {modes.map(({ mode, icon: Icon, label }) => (
        <Button
          key={mode}
          variant={viewMode === mode ? "default" : "ghost"}
          size="sm"
          onClick={() => setViewMode(mode)}
          className="gap-1.5"
        >
          <Icon className="h-4 w-4" />
          <span>{label}</span>
        </Button>
      ))}
    </div>
  );
}

// Editor toolbar component (extracted for reuse)
function EditorToolbar({
  blockCount,
  wordCount,
  readingTime,
  undo,
  redo,
  canUndo,
  canRedo,
  currentPost,
}: {
  blockCount: number;
  wordCount: number;
  readingTime: number;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  currentPost: { id: number; title: string } | null;
}) {
  return (
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
          <span>
            {blockCount} block{blockCount !== 1 ? "s" : ""}
          </span>
          {wordCount > 0 && (
            <>
              <span>•</span>
              <span>
                {wordCount} word{wordCount !== 1 ? "s" : ""}
              </span>
              <span>•</span>
              <span>{readingTime} min read</span>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {currentPost && <PostSettingsDialog />}
        <DesignSystemPanel />
        <RevisionTimeline />
        {currentPost && currentPost.title && (
          <span className="text-xs text-muted-foreground truncate max-w-[200px]">
            {currentPost.title}
          </span>
        )}
      </div>
    </div>
  );
}
