"use client";

import { useRef, useCallback } from "react";
import type { BlockProps, ListAttributes } from "@/types/blocks";

export function ListBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ListAttributes>) {
  const ref = useRef<HTMLElement>(null);
  const Tag = attributes.ordered ? "ol" : "ul";

  const handleBlur = useCallback(() => {
    if (ref.current) {
      const values = ref.current.innerHTML;
      if (values !== attributes.values) {
        onUpdate({ values });
      }
    }
  }, [attributes.values, onUpdate]);

  const toggleOrdered = useCallback(() => {
    onUpdate({ ordered: !attributes.ordered });
  }, [attributes.ordered, onUpdate]);

  return (
    <div className="relative group">
      {isSelected && (
        <div className="absolute -top-8 left-0 flex gap-0.5 bg-background border rounded-md shadow-sm p-0.5 z-10">
          <button
            onClick={() => onUpdate({ ordered: false })}
            className={`px-2 py-1 text-xs rounded ${
              !attributes.ordered ? "bg-primary text-primary-foreground" : "hover:bg-accent"
            }`}
          >
            Bullet
          </button>
          <button
            onClick={() => onUpdate({ ordered: true })}
            className={`px-2 py-1 text-xs rounded ${
              attributes.ordered ? "bg-primary text-primary-foreground" : "hover:bg-accent"
            }`}
          >
            Numbered
          </button>
        </div>
      )}
      <Tag
        ref={ref as React.Ref<HTMLOListElement & HTMLUListElement>}
        className={`block-content list-inside ${
          attributes.ordered ? "list-decimal" : "list-disc"
        } space-y-1 ${isSelected ? "ring-2 ring-primary/20 rounded p-2" : ""}`}
        contentEditable
        suppressContentEditableWarning
        onBlur={handleBlur}
        dangerouslySetInnerHTML={{ __html: attributes.values || "<li></li>" }}
      />
    </div>
  );
}
