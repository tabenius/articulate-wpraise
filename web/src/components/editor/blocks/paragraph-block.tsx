"use client";

import { useRef, useCallback } from "react";
import type { BlockProps, ParagraphAttributes } from "@/types/blocks";

export function ParagraphBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ParagraphAttributes>) {
  const ref = useRef<HTMLParagraphElement>(null);

  const handleBlur = useCallback(() => {
    if (ref.current) {
      const content = ref.current.innerHTML;
      if (content !== attributes.content) {
        onUpdate({ content });
      }
    }
  }, [attributes.content, onUpdate]);

  return (
    <p
      ref={ref}
      className={`block-content min-h-[1.5em] ${
        attributes.align ? `text-${attributes.align}` : ""
      } ${isSelected ? "ring-2 ring-primary/20 rounded" : ""}`}
      contentEditable
      suppressContentEditableWarning
      onBlur={handleBlur}
      dangerouslySetInnerHTML={{ __html: attributes.content || "" }}
    />
  );
}
