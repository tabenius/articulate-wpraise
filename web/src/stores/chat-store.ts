import { create } from "zustand";
import type { Message, ToolCall } from "@/types/chat";

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentStreamContent: string;
  currentToolCalls: ToolCall[];

  addMessage: (message: Message) => void;
  setStreaming: (streaming: boolean) => void;
  appendStreamContent: (chunk: string) => void;
  addToolCall: (toolCall: ToolCall) => void;
  updateToolCall: (id: string, update: Partial<ToolCall>) => void;
  finalizeStream: () => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentStreamContent: "",
  currentToolCalls: [],

  addMessage: (message) => {
    set((state) => ({ messages: [...state.messages, message] }));
  },

  setStreaming: (streaming) => {
    set({ isStreaming: streaming });
    if (streaming) {
      set({ currentStreamContent: "", currentToolCalls: [] });
    }
  },

  appendStreamContent: (chunk) => {
    set((state) => ({
      currentStreamContent: state.currentStreamContent + chunk,
    }));
  },

  addToolCall: (toolCall) => {
    set((state) => ({
      currentToolCalls: [...state.currentToolCalls, toolCall],
    }));
  },

  updateToolCall: (id, update) => {
    set((state) => ({
      currentToolCalls: state.currentToolCalls.map((tc) =>
        tc.id === id ? { ...tc, ...update } : tc
      ),
    }));
  },

  finalizeStream: () => {
    const { currentStreamContent, currentToolCalls } = get();
    if (currentStreamContent || currentToolCalls.length > 0) {
      const message: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: currentStreamContent,
        timestamp: Date.now(),
        toolCalls: currentToolCalls.length > 0 ? currentToolCalls : undefined,
      };
      set((state) => ({
        messages: [...state.messages, message],
        isStreaming: false,
        currentStreamContent: "",
        currentToolCalls: [],
      }));
    } else {
      set({ isStreaming: false });
    }
  },

  clearMessages: () => {
    set({ messages: [], currentStreamContent: "", currentToolCalls: [] });
  },
}));
