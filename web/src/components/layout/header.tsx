"use client";

import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConnectionSwitcher } from "@/components/header/connection-switcher";
import { UserMenu } from "@/components/header/user-menu";
import {
  Undo2,
  Redo2,
  Save,
  Settings,
  FileText,
  Keyboard,
} from "lucide-react";

interface HeaderProps {
  onOpenSettings: () => void;
  onOpenPostList: () => void;
  onSave: () => void;
  onOpenShortcuts?: () => void;
}

export function Header({ onOpenSettings, onOpenPostList, onSave, onOpenShortcuts }: HeaderProps) {
  const currentPost = usePostStore((s) => s.currentPost);
  const isDirty = useEditorStore((s) => s.isDirty);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const historyIndex = useEditorStore((s) => s.historyIndex);
  const historyLength = useEditorStore((s) => s.history.length);

  return (
    <header className="flex items-center justify-between h-14 px-4 border-b bg-background">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold tracking-tight">WP-AI</h1>

        <Button variant="ghost" size="sm" onClick={onOpenPostList}>
          <FileText className="h-4 w-4 mr-2" />
          {currentPost ? currentPost.title : "Select Post"}
        </Button>

        {currentPost && (
          <Badge variant={isDirty ? "destructive" : "secondary"}>
            {isDirty ? "Unsaved" : currentPost.status}
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={undo}
          disabled={historyIndex <= 0}
          title="Undo"
        >
          <Undo2 className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={redo}
          disabled={historyIndex >= historyLength - 1}
          title="Redo"
        >
          <Redo2 className="h-4 w-4" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onSave}
          disabled={!isDirty}
          title="Save (Cmd+S)"
        >
          <Save className="h-4 w-4 mr-2" />
          Save
        </Button>

        {onOpenShortcuts && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onOpenShortcuts}
            title="Keyboard Shortcuts (?)"
          >
            <Keyboard className="h-4 w-4" />
          </Button>
        )}

        <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings">
          <Settings className="h-4 w-4" />
        </Button>

        <div className="ml-2 pl-2 border-l flex items-center gap-2">
          <ConnectionSwitcher />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
