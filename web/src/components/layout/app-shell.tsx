"use client";

import { useState, useCallback, useEffect } from "react";
import { Header } from "./header";
import { SplitView } from "./split-view";
import { Sidebar } from "./sidebar";
import { ChatPanel } from "@/components/chat/chat-panel";
import { EditorPanel } from "@/components/editor/editor-panel";
import { SettingsDialog } from "@/components/settings-dialog";
import { KeyboardShortcutsDialog } from "@/components/keyboard-shortcuts-dialog";
import { TooltipProvider } from "@/components/ui/tooltip";

interface AppShellProps {
  onLoadPost: (postId: number) => void;
  onLoadPosts: () => void;
  onSave: () => void;
  onCreatePost: () => void;
}

export function AppShell({ onLoadPost, onLoadPosts, onSave, onCreatePost }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  // Listen for ? key to open shortcuts dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        // Check if user is not in an input field
        const target = e.target as HTMLElement;
        const isInput =
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable;

        if (!isInput) {
          e.preventDefault();
          setShortcutsOpen(true);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleOpenPostList = useCallback(() => {
    onLoadPosts();
    setSidebarOpen(true);
  }, [onLoadPosts]);

  const handleSelectPost = useCallback(
    (postId: number) => {
      onLoadPost(postId);
      setSidebarOpen(false);
    },
    [onLoadPost]
  );

  return (
    <TooltipProvider>
      <div className="h-screen flex flex-col relative">
        <Header
          onOpenSettings={() => setSettingsOpen(true)}
          onOpenPostList={handleOpenPostList}
          onSave={onSave}
          onOpenShortcuts={() => setShortcutsOpen(true)}
        />

        <div className="flex-1 overflow-hidden">
          <SplitView
            left={<ChatPanel />}
            right={<EditorPanel />}
          />
        </div>

        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onSelectPost={handleSelectPost}
          onCreatePost={() => {
            onCreatePost();
            setSidebarOpen(false);
          }}
        />

        <SettingsDialog
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
        />

        <KeyboardShortcutsDialog
          open={shortcutsOpen}
          onOpenChange={setShortcutsOpen}
        />
      </div>
    </TooltipProvider>
  );
}
