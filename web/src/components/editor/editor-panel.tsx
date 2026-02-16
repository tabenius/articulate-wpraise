"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { BlockEditor } from "./block-editor";
import { BlockToolbar } from "./block-toolbar";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { Undo2, Redo2 } from "lucide-react";

export function EditorPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const blockCount = useEditorStore((s) => s.blocks.length);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const canUndo = useEditorStore((s) => s.canUndo());
  const canRedo = useEditorStore((s) => s.canRedo());

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
