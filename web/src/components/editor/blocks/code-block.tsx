"use client";

import { useRef, useCallback } from "react";
import type { BlockProps, CodeAttributes } from "@/types/blocks";

export function CodeBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<CodeAttributes>) {
  const ref = useRef<HTMLElement>(null);

  const handleBlur = useCallback(() => {
    if (ref.current) {
      const content = ref.current.textContent || "";
      if (content !== attributes.content) {
        onUpdate({ content });
      }
    }
  }, [attributes.content, onUpdate]);

  return (
    <pre
      className={`bg-muted rounded-lg p-4 overflow-x-auto ${
        isSelected ? "ring-2 ring-primary/20" : ""
      }`}
    >
      <code
        ref={ref}
        className="block-content text-sm font-mono whitespace-pre"
        contentEditable
        suppressContentEditableWarning
        onBlur={handleBlur}
      >
        {attributes.content || ""}
      </code>
    </pre>
  );
}
