"use client";

import type { BlockProps, HeadingAttributes } from "@/types/blocks";
import { RichTextEditor } from "../rich-text-editor";

export function HeadingBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<HeadingAttributes>) {
  const level = attributes.level || 2;

  const handleChange = (html: string) => {
    if (html !== attributes.content) {
      onUpdate({ content: html });
    }
  };

  const handleLevelChange = (newLevel: number) => {
    onUpdate({ level: newLevel as HeadingAttributes["level"] });
  };

  const sizeClasses: Record<number, string> = {
    1: "text-4xl font-bold",
    2: "text-3xl font-bold",
    3: "text-2xl font-semibold",
    4: "text-xl font-semibold",
    5: "text-lg font-medium",
    6: "text-base font-medium",
  };

  const className = `${sizeClasses[level] || sizeClasses[2]} ${
    attributes.textAlign ? `text-${attributes.textAlign}` : ""
  }`;

  return (
    <div className="relative group">
      {isSelected && (
        <div className="absolute -top-8 left-0 flex gap-0.5 bg-background border rounded-md shadow-sm p-0.5 z-10">
          {[1, 2, 3, 4, 5, 6].map((l) => (
            <button
              key={l}
              onClick={() => handleLevelChange(l)}
              className={`px-2 py-1 text-xs rounded ${
                level === l
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent"
              }`}
            >
              H{l}
            </button>
          ))}
        </div>
      )}
      <RichTextEditor
        content={attributes.content || ""}
        placeholder={`Heading ${level}`}
        isSelected={isSelected}
        onChange={handleChange}
        className={className}
      />
    </div>
  );
}
