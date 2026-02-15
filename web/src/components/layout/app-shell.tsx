"use client";

import { useState, useCallback } from "react";
import { Header } from "./header";
import { SplitView } from "./split-view";
import { Sidebar } from "./sidebar";
import { ChatPanel } from "@/components/chat/chat-panel";
import { EditorPanel } from "@/components/editor/editor-panel";
import { SettingsDialog } from "@/components/settings-dialog";
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
      </div>
    </TooltipProvider>
  );
}
