"use client";

import { useEffect, useRef } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { usePostStore } from "@/stores/post-store";
import { useBlocks } from "./use-blocks";

const AUTOSAVE_DELAY = 2000; // 2 seconds

/**
 * Hook that auto-saves blocks to WordPress when the editor is dirty.
 */
export function useAutosave() {
  const isDirty = useEditorStore((s) => s.isDirty);
  const blocks = useEditorStore((s) => s.blocks);
  const readOnlyMode = usePostStore((s) => s.readOnlyMode);
  const { persistBlocks } = useBlocks();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isDirty || readOnlyMode) return;

    // Clear previous timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Set new debounced save
    timerRef.current = setTimeout(async () => {
      try {
        await persistBlocks();
      } catch (error) {
        console.error("Autosave failed:", error);
      }
    }, AUTOSAVE_DELAY);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [isDirty, blocks, persistBlocks, readOnlyMode]);
}
