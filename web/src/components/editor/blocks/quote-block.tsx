"use client";

import { useRef, useCallback } from "react";
import type { BlockProps, QuoteAttributes } from "@/types/blocks";

export function QuoteBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<QuoteAttributes>) {
  const valueRef = useRef<HTMLDivElement>(null);
  const citeRef = useRef<HTMLElement>(null);

  const handleValueBlur = useCallback(() => {
    if (valueRef.current) {
      const value = valueRef.current.innerHTML;
      if (value !== attributes.value) {
        onUpdate({ value });
      }
    }
  }, [attributes.value, onUpdate]);

  const handleCiteBlur = useCallback(() => {
    if (citeRef.current) {
      const citation = citeRef.current.textContent || "";
      if (citation !== attributes.citation) {
        onUpdate({ citation });
      }
    }
  }, [attributes.citation, onUpdate]);

  return (
    <blockquote
      className={`border-l-4 border-primary/30 pl-4 py-2 ${
        isSelected ? "ring-2 ring-primary/20 rounded" : ""
      }`}
    >
      <div
        ref={valueRef}
        className="block-content italic text-lg"
        contentEditable
        suppressContentEditableWarning
        onBlur={handleValueBlur}
        dangerouslySetInnerHTML={{ __html: attributes.value || "" }}
      />
      <cite
        ref={citeRef}
        className="block-content text-sm text-muted-foreground mt-2 block not-italic"
        contentEditable
        suppressContentEditableWarning
        onBlur={handleCiteBlur}
      >
        {attributes.citation || ""}
      </cite>
    </blockquote>
  );
}
