"use client";

import type { BlockProps, GroupAttributes } from "@/types/blocks";
import { BlockRenderer } from "../block-renderer";

export function GroupBlock({
  block,
  attributes,
  isSelected,
}: BlockProps<GroupAttributes>) {
  return (
    <div
      className={`space-y-2 ${
        isSelected ? "ring-2 ring-primary/20 rounded p-2" : ""
      }`}
    >
      {block.innerBlocks.length > 0 ? (
        block.innerBlocks.map((innerBlock) => (
          <BlockRenderer key={innerBlock.clientId} block={innerBlock} />
        ))
      ) : (
        <div className="min-h-[2rem] border border-dashed border-border rounded p-4 flex items-center justify-center text-muted-foreground text-sm">
          Empty group
        </div>
      )}
    </div>
  );
}
