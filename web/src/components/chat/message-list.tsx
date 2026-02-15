"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chat-store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { StreamingIndicator } from "./streaming-indicator";
import { Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";

export function MessageList() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const currentStreamContent = useChatStore((s) => s.currentStreamContent);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStreamContent, isStreaming]);

  return (
    <ScrollArea className="flex-1">
      <div className="p-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Bot className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium mb-1">WP-AI Assistant</p>
            <p className="text-sm text-center max-w-sm">
              Ask me to create, edit, or manage your WordPress content.
              I can add blocks, change text, and organize your posts.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming content */}
        {isStreaming && currentStreamContent && (
          <div className="flex gap-3">
            <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="inline-block max-w-[85%] rounded-2xl rounded-tl-sm bg-muted px-4 py-2.5 text-sm">
                <div className="message-content prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{currentStreamContent}</ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        )}

        {isStreaming && !currentStreamContent && <StreamingIndicator />}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
