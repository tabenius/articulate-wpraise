"use client";

import type { BlockProps, ColumnsAttributes } from "@/types/blocks";
import { BlockRenderer } from "../block-renderer";

export function ColumnsBlock({
  block,
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ColumnsAttributes>) {
  return (
    <div
      className={`grid gap-4 ${
        isSelected ? "ring-2 ring-primary/20 rounded p-2" : ""
      }`}
      style={{
        gridTemplateColumns: `repeat(${block.innerBlocks.length || 2}, 1fr)`,
      }}
    >
      {block.innerBlocks.map((innerBlock) => (
        <div key={innerBlock.clientId} className="min-h-[2rem] border border-dashed border-border rounded p-2">
          <BlockRenderer block={innerBlock} />
        </div>
      ))}
      {block.innerBlocks.length === 0 && (
        <>
          <div className="min-h-[4rem] border border-dashed border-border rounded p-2 flex items-center justify-center text-muted-foreground text-sm">
            Column 1
          </div>
          <div className="min-h-[4rem] border border-dashed border-border rounded p-2 flex items-center justify-center text-muted-foreground text-sm">
            Column 2
          </div>
        </>
      )}
    </div>
  );
}
