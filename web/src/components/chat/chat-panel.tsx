"use client";

import { useCallback, useRef } from "react";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { useChatStore } from "@/stores/chat-store";
import { usePostStore } from "@/stores/post-store";
import { useToast } from "@/hooks/use-toast";
import type { Message } from "@/types/chat";

const CHAT_TIMEOUT = 120000; // 2 minutes for long AI responses

export function ChatPanel() {
  const addMessage = useChatStore((s) => s.addMessage);
  const setStreaming = useChatStore((s) => s.setStreaming);
  const appendStreamContent = useChatStore((s) => s.appendStreamContent);
  const addToolCall = useChatStore((s) => s.addToolCall);
  const updateToolCall = useChatStore((s) => s.updateToolCall);
  const finalizeStream = useChatStore((s) => s.finalizeStream);
  const messages = useChatStore((s) => s.messages);
  const currentPost = usePostStore((s) => s.currentPost);
  const { toast } = useToast();
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(
    async (content: string) => {
      // Validate input
      if (!content || typeof content !== "string" || !content.trim()) {
        toast({
          variant: "destructive",
          title: "Invalid message",
          description: "Please enter a message",
        });
        return;
      }

      // Abort previous request if still running
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();
      const { signal } = abortControllerRef.current;

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
        timestamp: Date.now(),
      };
      addMessage(userMessage);
      setStreaming(true);

      // Set timeout
      const timeoutId = setTimeout(() => {
        abortControllerRef.current?.abort();
      }, CHAT_TIMEOUT);

      try {
        // Get API key from localStorage (BYOK)
        const storedKey =
          typeof window !== "undefined"
            ? localStorage.getItem("articulate-api-key")
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
              { role: "user", content: content.trim() },
            ],
            postId: currentPost?.id,
          }),
          signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          let errorText: string;
          try {
            errorText = await response.text();
          } catch {
            errorText = `HTTP ${response.status}`;
          }
          throw new Error(errorText || `HTTP ${response.status}`);
        }

        // Parse SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body - the server did not return a stream");
        }

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
                appendStreamContent(event.content || "");
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
                appendStreamContent(`\n\nError: ${event.content || "Unknown error"}`);
              }
            } catch (parseError) {
              // Log malformed JSON for debugging
              console.warn("Failed to parse SSE event:", data, parseError);
            }
          }
        }
      } catch (error) {
        clearTimeout(timeoutId);

        // Handle abort/timeout
        if (error instanceof Error && error.name === "AbortError") {
          const errorMsg = "Request cancelled or timed out";
          appendStreamContent(`\n\n${errorMsg}`);
          toast({
            variant: "destructive",
            title: "Request timeout",
            description: "The request took too long. Please try again.",
          });
          return;
        }

        // Handle other errors
        const errorMsg = error instanceof Error ? error.message : "Unknown error";
        appendStreamContent(`\n\nFailed to get response: ${errorMsg}`);
        toast({
          variant: "destructive",
          title: "Chat error",
          description: errorMsg,
        });
        console.error("Chat error:", error);
      } finally {
        clearTimeout(timeoutId);
        finalizeStream();
        abortControllerRef.current = null;
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
      toast,
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
