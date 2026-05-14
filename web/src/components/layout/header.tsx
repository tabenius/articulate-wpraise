"use client";

import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConnectionSwitcher } from "@/components/header/connection-switcher";
import { UserMenu } from "@/components/header/user-menu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Undo2,
  Redo2,
  Save,
  Settings,
  FileText,
  Keyboard,
  Plus,
  File,
  Layout,
} from "lucide-react";
import Link from "next/link";

interface HeaderProps {
  onOpenSettings: () => void;
  onOpenPostList: () => void;
  onSave: () => void;
  onOpenShortcuts?: () => void;
  onCreatePost?: () => void;
  onCreatePage?: () => void;
}

export function Header({ onOpenSettings, onOpenPostList, onSave, onOpenShortcuts, onCreatePost, onCreatePage }: HeaderProps) {
  const currentPost = usePostStore((s) => s.currentPost);
  const isDirty = useEditorStore((s) => s.isDirty);
  const syncState = usePostStore((s) => s.syncState);
  const readOnlyMode = usePostStore((s) => s.readOnlyMode);
  const dataSource = usePostStore((s) => s.dataSource);
  const blocks = useEditorStore((s) => s.blocks);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const historyIndex = useEditorStore((s) => s.historyIndex);
  const historyLength = useEditorStore((s) => s.history.length);

  // Calculate content statistics
  const blockCount = blocks.length;

  const wordCount = blocks.reduce((total, block) => {
    const text = (block.attributes as any)?.content || "";
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    return total + words;
  }, 0);

  const readTime = Math.max(1, Math.ceil(wordCount / 200)); // 200 words per minute

  return (
    <header className="flex items-center justify-between h-14 px-4 border-b bg-background">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Articulate</h1>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="default" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {onCreatePost && (
              <DropdownMenuItem onClick={onCreatePost}>
                <FileText className="h-4 w-4 mr-2" />
                New Post
              </DropdownMenuItem>
            )}
            {onCreatePage && (
              <DropdownMenuItem onClick={onCreatePage}>
                <File className="h-4 w-4 mr-2" />
                New Page
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="ghost" size="sm" onClick={onOpenPostList}>
          <FileText className="h-4 w-4 mr-2" />
          {currentPost ? currentPost.title : "Select Post"}
        </Button>

        <Link href="/site-editor">
          <Button variant="ghost" size="sm">
            <Layout className="h-4 w-4 mr-2" />
            Site Editor
          </Button>
        </Link>

        {currentPost && (
          <>
            <Badge variant={isDirty ? "destructive" : "secondary"}>
              {isDirty ? "Unsaved" : currentPost.status}
            </Badge>
            {readOnlyMode && <Badge variant="destructive">Read-only fallback</Badge>}
            {!readOnlyMode && syncState === "saving" && <Badge variant="outline">Syncing...</Badge>}
            {!readOnlyMode && syncState === "synced" && <Badge variant="secondary">Synced</Badge>}
            {syncState === "error" && <Badge variant="destructive">Sync error</Badge>}
            {dataSource === "cache" && <Badge variant="outline">Cached data</Badge>}
            {blockCount > 0 && (
              <div className="text-xs text-muted-foreground flex items-center gap-3 px-3 py-1 rounded-md bg-muted/50">
                <span>{blockCount} block{blockCount !== 1 ? 's' : ''}</span>
                <span>•</span>
                <span>{wordCount} word{wordCount !== 1 ? 's' : ''}</span>
                {wordCount > 0 && (
                  <>
                    <span>•</span>
                    <span>{readTime} min read</span>
                  </>
                )}
              </div>
            )}
          </>
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
