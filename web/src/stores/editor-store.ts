import { create } from "zustand";
import type { Block } from "@/types/blocks";

interface EditorState {
  blocks: Block[];
  selectedBlockId: string | null;
  isDirty: boolean;
  history: Block[][];
  historyIndex: number;
  lastHistoryPush: number;

  setBlocks: (blocks: Block[]) => void;
  updateBlock: (clientId: string, attributes: Record<string, unknown>) => void;
  addBlock: (block: Block, position?: number) => void;
  removeBlock: (clientId: string) => void;
  moveBlock: (clientId: string, newPosition: number) => void;
  selectBlock: (clientId: string | null) => void;
  setDirty: (dirty: boolean) => void;
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  blocks: [],
  selectedBlockId: null,
  isDirty: false,
  history: [],
  historyIndex: -1,
  lastHistoryPush: 0,

  setBlocks: (blocks) => {
    // Validate input
    if (!Array.isArray(blocks)) {
      console.error("setBlocks: invalid blocks array", blocks);
      return;
    }
    set({ blocks, isDirty: false, history: [blocks], historyIndex: 0 });
  },

  updateBlock: (clientId, attributes) => {
    // Validate input
    if (!clientId || typeof clientId !== "string") {
      console.error("updateBlock: invalid clientId", clientId);
      return;
    }
    if (!attributes || typeof attributes !== "object") {
      console.error("updateBlock: invalid attributes", attributes);
      return;
    }

    const { blocks } = get();
    if (!Array.isArray(blocks)) {
      console.error("updateBlock: blocks is not an array");
      return;
    }

    const updated = updateBlockRecursive(blocks, clientId, attributes);
    get().pushHistory();
    set({ blocks: updated, isDirty: true });
  },

  addBlock: (block, position) => {
    const { blocks } = get();
    const newBlocks = [...blocks];
    if (position === undefined || position === -1 || position >= blocks.length) {
      newBlocks.push(block);
    } else {
      newBlocks.splice(position, 0, block);
    }
    get().pushHistory();
    set({ blocks: newBlocks, isDirty: true, selectedBlockId: block.clientId });
  },

  removeBlock: (clientId) => {
    // Validate input
    if (!clientId || typeof clientId !== "string") {
      console.error("removeBlock: invalid clientId", clientId);
      return;
    }

    const { blocks, selectedBlockId } = get();
    if (!Array.isArray(blocks)) {
      console.error("removeBlock: blocks is not an array");
      return;
    }

    const filtered = blocks.filter((b) => b.clientId !== clientId);
    get().pushHistory();
    set({
      blocks: filtered,
      isDirty: true,
      selectedBlockId: selectedBlockId === clientId ? null : selectedBlockId,
    });
  },

  moveBlock: (clientId, newPosition) => {
    // Validate input
    if (!clientId || typeof clientId !== "string") {
      console.error("moveBlock: invalid clientId", clientId);
      return;
    }
    if (typeof newPosition !== "number" || newPosition < 0) {
      console.error("moveBlock: invalid newPosition", newPosition);
      return;
    }

    const { blocks } = get();
    if (!Array.isArray(blocks)) {
      console.error("moveBlock: blocks is not an array");
      return;
    }

    const index = blocks.findIndex((b) => b.clientId === clientId);
    if (index === -1) {
      console.warn("moveBlock: block not found", clientId);
      return;
    }

    const newBlocks = [...blocks];
    const [moved] = newBlocks.splice(index, 1);
    const pos = Math.max(0, Math.min(newPosition, newBlocks.length));
    newBlocks.splice(pos, 0, moved);
    get().pushHistory();
    set({ blocks: newBlocks, isDirty: true });
  },

  selectBlock: (clientId) => {
    set({ selectedBlockId: clientId });
  },

  setDirty: (dirty) => {
    set({ isDirty: dirty });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      set({
        blocks: history[newIndex],
        historyIndex: newIndex,
        isDirty: true,
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      set({
        blocks: history[newIndex],
        historyIndex: newIndex,
        isDirty: true,
      });
    }
  },

  pushHistory: () => {
    const { blocks, history, historyIndex, lastHistoryPush } = get();
    const now = Date.now();

    // Debounce: only push if more than 500ms since last push
    if (now - lastHistoryPush < 500) {
      return;
    }

    // Validate blocks array
    if (!Array.isArray(blocks)) {
      console.error("pushHistory: blocks is not an array", blocks);
      return;
    }

    const newHistory = history.slice(0, historyIndex + 1);

    // Deep clone blocks with fallback
    let clonedBlocks: Block[];
    try {
      clonedBlocks = structuredClone(blocks);
    } catch (error) {
      console.warn("structuredClone failed, using JSON fallback:", error);
      try {
        clonedBlocks = JSON.parse(JSON.stringify(blocks));
      } catch (jsonError) {
        console.error("Failed to clone blocks:", jsonError);
        return;
      }
    }

    newHistory.push(clonedBlocks);
    // Keep max 50 history entries
    if (newHistory.length > 50) newHistory.shift();
    set({
      history: newHistory,
      historyIndex: newHistory.length - 1,
      lastHistoryPush: now,
    });
  },

  canUndo: () => {
    const { historyIndex } = get();
    return historyIndex > 0;
  },

  canRedo: () => {
    const { history, historyIndex } = get();
    return historyIndex < history.length - 1;
  },
}));

function updateBlockRecursive(
  blocks: Block[],
  clientId: string,
  attributes: Record<string, unknown>
): Block[] {
  return blocks.map((block) => {
    if (block.clientId === clientId) {
      return { ...block, attributes: { ...block.attributes, ...attributes } };
    }
    if (block.innerBlocks.length > 0) {
      return {
        ...block,
        innerBlocks: updateBlockRecursive(block.innerBlocks, clientId, attributes),
      };
    }
    return block;
  });
}
