"use client";

import { useCallback } from "react";
import type { BlockProps, ButtonAttributes } from "@/types/blocks";

export function ButtonsBlock({
  block,
  isSelected,
}: BlockProps<Record<string, unknown>>) {
  return (
    <div
      className={`flex gap-2 flex-wrap ${
        isSelected ? "ring-2 ring-primary/20 rounded p-2" : ""
      }`}
    >
      {block.innerBlocks.map((btn) => (
        <ButtonItem key={btn.clientId} attributes={btn.attributes as ButtonAttributes} />
      ))}
      {block.innerBlocks.length === 0 && (
        <span className="text-sm text-muted-foreground">No buttons</span>
      )}
    </div>
  );
}

function ButtonItem({ attributes }: { attributes: ButtonAttributes }) {
  return (
    <span className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium">
      {attributes.text || "Button"}
    </span>
  );
}
