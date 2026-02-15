"use client";

import type { BlockProps, SpacerAttributes } from "@/types/blocks";

export function SpacerBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<SpacerAttributes>) {
  const height = attributes.height || "100px";

  return (
    <div
      className={`relative ${
        isSelected ? "ring-2 ring-primary/20 rounded" : ""
      }`}
      style={{ height }}
    >
      {isSelected && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center gap-2 bg-background border rounded-md shadow-sm px-3 py-1.5">
            <label className="text-xs text-muted-foreground">Height:</label>
            <input
              type="text"
              value={height}
              onChange={(e) => onUpdate({ height: e.target.value })}
              className="w-20 px-2 py-1 text-xs border rounded bg-background"
            />
          </div>
        </div>
      )}
      <div className="w-full h-full border border-dashed border-border" />
    </div>
  );
}
