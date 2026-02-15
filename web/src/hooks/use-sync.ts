"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chat-store";
import { useBlocks } from "./use-blocks";

/**
 * Hook that bridges chat tool results to editor state.
 *
 * When the AI makes block-related tool calls (insert_block, update_blocks, etc.),
 * this hook detects those results and refreshes the editor's block tree from
 * WordPress to stay in sync.
 */

const BLOCK_TOOLS = new Set([
  "update_blocks",
  "insert_block",
  "remove_block",
  "move_block",
  "create_post",
  "update_post",
]);

export function useSync() {
  const messages = useChatStore((s) => s.messages);
  const { refreshBlocks } = useBlocks();
  const lastMessageCountRef = useRef(0);

  useEffect(() => {
    // Only process new messages
    if (messages.length <= lastMessageCountRef.current) return;
    lastMessageCountRef.current = messages.length;

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== "assistant") return;

    // Check if any tool calls affected blocks
    const toolCalls = lastMessage.toolCalls;
    if (!toolCalls || toolCalls.length === 0) return;

    const hasBlockChange = toolCalls.some(
      (tc) => BLOCK_TOOLS.has(tc.name) && tc.status === "success"
    );

    if (hasBlockChange) {
      // Refresh blocks from WordPress after a short delay
      // to ensure the MCP server has finished writing
      setTimeout(() => {
        refreshBlocks();
      }, 500);
    }
  }, [messages, refreshBlocks]);
}
