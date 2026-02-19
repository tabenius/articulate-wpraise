"use client";

import type { BlockProps, ParagraphAttributes } from "@/types/blocks";
import { RichTextEditor } from "../rich-text-editor";

export function ParagraphBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ParagraphAttributes>) {
  const handleChange = (html: string) => {
    if (html !== attributes.content) {
      onUpdate({ content: html });
    }
  };

  return (
    <RichTextEditor
      content={attributes.content || ""}
      placeholder="Write a paragraph..."
      isSelected={isSelected}
      onChange={handleChange}
      className={attributes.align ? `text-${attributes.align}` : ""}
    />
  );
}
