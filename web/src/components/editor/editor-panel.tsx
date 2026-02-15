"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { BlockEditor } from "./block-editor";
import { BlockToolbar } from "./block-toolbar";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";

export function EditorPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const blockCount = useEditorStore((s) => s.blocks.length);

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Editor toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <BlockToolbar />
          <span className="text-xs text-muted-foreground">
            {blockCount} block{blockCount !== 1 ? "s" : ""}
          </span>
        </div>
        {currentPost && (
          <span className="text-xs text-muted-foreground truncate max-w-[200px]">
            {currentPost.title}
          </span>
        )}
      </div>

      {/* Editor content */}
      <ScrollArea className="flex-1">
        <BlockEditor />
      </ScrollArea>
    </div>
  );
}
