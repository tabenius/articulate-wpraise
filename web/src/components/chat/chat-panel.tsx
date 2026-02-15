"use client";

import { useCallback } from "react";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { useChatStore } from "@/stores/chat-store";
import { usePostStore } from "@/stores/post-store";
import type { Message } from "@/types/chat";

export function ChatPanel() {
  const addMessage = useChatStore((s) => s.addMessage);
  const setStreaming = useChatStore((s) => s.setStreaming);
  const appendStreamContent = useChatStore((s) => s.appendStreamContent);
  const addToolCall = useChatStore((s) => s.addToolCall);
  const updateToolCall = useChatStore((s) => s.updateToolCall);
  const finalizeStream = useChatStore((s) => s.finalizeStream);
  const messages = useChatStore((s) => s.messages);
  const currentPost = usePostStore((s) => s.currentPost);

  const handleSend = useCallback(
    async (content: string) => {
      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: Date.now(),
      };
      addMessage(userMessage);
      setStreaming(true);

      try {
        // Get API key from localStorage (BYOK)
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
              ...messages.map((m) => ({
                role: m.role,
                content: m.content,
              })),
              { role: "user", content },
            ],
            postId: currentPost?.id,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `HTTP ${response.status}`);
        }

        // Parse SSE stream
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

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="px-4 py-2 border-b bg-muted/30">
        <h2 className="text-sm font-medium">Chat</h2>
        <p className="text-xs text-muted-foreground">
          {currentPost
            ? `Editing: ${currentPost.title}`
            : "Select a post to start editing"}
        </p>
      </div>
      <MessageList />
      <ChatInput onSend={handleSend} />
    </div>
  );
}
