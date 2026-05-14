"use client";

import { useCallback } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { usePostStore } from "@/stores/post-store";
import { fetchBlocks, saveBlocks } from "@/lib/api";
import type { Block } from "@/types/blocks";

/**
 * Hook for block CRUD operations with WordPress sync.
 */
export function useBlocks() {
  const setBlocks = useEditorStore((s) => s.setBlocks);
  const blocks = useEditorStore((s) => s.blocks);
  const setDirty = useEditorStore((s) => s.setDirty);
  const currentPost = usePostStore((s) => s.currentPost);
  const setSyncState = usePostStore((s) => s.setSyncState);
  const setReadOnlyMode = usePostStore((s) => s.setReadOnlyMode);
  const setLastSyncedAt = usePostStore((s) => s.setLastSyncedAt);

  const loadBlocks = useCallback(
    async (postId: number) => {
      try {
        const result = await fetchBlocks(postId);
        if (Array.isArray(result)) {
          setBlocks(result);
          setSyncState("synced");
        }
      } catch (error) {
        console.error("Failed to load blocks:", error);
        setSyncState("error");
      }
    },
    [setBlocks, setSyncState]
  );

  const persistBlocks = useCallback(async () => {
    if (!currentPost) return;

    try {
      setSyncState("saving");
      await saveBlocks(currentPost.id, blocks);
      setDirty(false);
      setReadOnlyMode(false);
      setSyncState("synced");
      setLastSyncedAt(new Date().toISOString());
    } catch (error) {
      console.error("Failed to save blocks:", error);
      setSyncState("error");
      setReadOnlyMode(true);
      throw error;
    }
  }, [currentPost, blocks, setDirty, setSyncState, setReadOnlyMode, setLastSyncedAt]);

  const refreshBlocks = useCallback(async () => {
    if (!currentPost) return;
    await loadBlocks(currentPost.id);
  }, [currentPost, loadBlocks]);

  return {
    loadBlocks,
    persistBlocks,
    refreshBlocks,
  };
}
