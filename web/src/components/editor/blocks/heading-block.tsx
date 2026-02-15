"use client";

import { useRef, useCallback } from "react";
import type { BlockProps, HeadingAttributes } from "@/types/blocks";

export function HeadingBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<HeadingAttributes>) {
  const ref = useRef<HTMLHeadingElement>(null);
  const level = attributes.level || 2;

  const handleBlur = useCallback(() => {
    if (ref.current) {
      const content = ref.current.innerHTML;
      if (content !== attributes.content) {
        onUpdate({ content });
      }
    }
  }, [attributes.content, onUpdate]);

  const handleLevelChange = useCallback(
    (newLevel: number) => {
      onUpdate({ level: newLevel as HeadingAttributes["level"] });
    },
    [onUpdate]
  );

  const Tag = `h${level}` as keyof JSX.IntrinsicElements;
  const sizeClasses: Record<number, string> = {
    1: "text-4xl font-bold",
    2: "text-3xl font-bold",
    3: "text-2xl font-semibold",
    4: "text-xl font-semibold",
    5: "text-lg font-medium",
    6: "text-base font-medium",
  };

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
      <Tag
        ref={ref as React.Ref<HTMLHeadingElement>}
        className={`block-content ${sizeClasses[level] || sizeClasses[2]} ${
          attributes.textAlign ? `text-${attributes.textAlign}` : ""
        } ${isSelected ? "ring-2 ring-primary/20 rounded" : ""}`}
        contentEditable
        suppressContentEditableWarning
        onBlur={handleBlur}
        dangerouslySetInnerHTML={{ __html: attributes.content || "" }}
      />
    </div>
  );
}
