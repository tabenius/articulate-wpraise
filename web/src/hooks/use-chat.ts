/**
 * Hook for chat functionality.
 * Re-exports the chat logic from the ChatPanel for use in other components.
 */

import { useCallback } from "react";
import { useChatStore } from "@/stores/chat-store";
import { usePostStore } from "@/stores/post-store";
import type { Message } from "@/types/chat";

export function useChat() {
  const addMessage = useChatStore((s) => s.addMessage);
  const setStreaming = useChatStore((s) => s.setStreaming);
  const appendStreamContent = useChatStore((s) => s.appendStreamContent);
  const addToolCall = useChatStore((s) => s.addToolCall);
  const updateToolCall = useChatStore((s) => s.updateToolCall);
  const finalizeStream = useChatStore((s) => s.finalizeStream);
  const messages = useChatStore((s) => s.messages);
  const currentPost = usePostStore((s) => s.currentPost);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: Date.now(),
      };
      addMessage(userMessage);
      setStreaming(true);

      try {
        const storedKey =
          typeof window !== "undefined"
            ? localStorage.getItem("wp-ai-api-key")
            : null;

        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(storedKey ? { "X-API-Key": storedKey } : {}),
          },
          body: JSON.stringify({
            messages: [
              ...messages.map((m) => ({ role: m.role, content: m.content })),
              { role: "user", content },
            ],
            postId: currentPost?.id,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") continue;

            try {
              const event = JSON.parse(data);
              if (event.type === "text") {
                appendStreamContent(event.content);
              } else if (event.type === "tool_use") {
                addToolCall({
                  id: event.id,
                  name: event.name,
                  input: event.input,
                  status: "running",
                });
              } else if (event.type === "tool_result") {
                updateToolCall(event.id, {
                  result: event.result,
                  status: event.error ? "error" : "success",
                });
              } else if (event.type === "error") {
                appendStreamContent(`\n\nError: ${event.content}`);
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      } catch (error) {
        const errorMsg =
          error instanceof Error ? error.message : "Unknown error";
        appendStreamContent(`\n\nFailed to get response: ${errorMsg}`);
      } finally {
        finalizeStream();
      }
    },
    [
      addMessage,
      setStreaming,
      appendStreamContent,
      addToolCall,
      updateToolCall,
      finalizeStream,
      messages,
      currentPost,
    ]
  );

  return { sendMessage };
}
