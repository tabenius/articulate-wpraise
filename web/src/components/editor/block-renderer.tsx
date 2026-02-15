"use client";

import { useCallback } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { BLOCK_COMPONENTS } from "./blocks";
import { BLOCK_LABELS } from "@/types/blocks";
import type { Block } from "@/types/blocks";

interface BlockRendererProps {
  block: Block;
}

export function BlockRenderer({ block }: BlockRendererProps) {
  const selectedBlockId = useEditorStore((s) => s.selectedBlockId);
  const updateBlock = useEditorStore((s) => s.updateBlock);

  const isSelected = selectedBlockId === block.clientId;
  const Component = BLOCK_COMPONENTS[block.name];

  const handleUpdate = useCallback(
    (attributes: Record<string, unknown>) => {
      updateBlock(block.clientId, attributes);
    },
    [block.clientId, updateBlock]
  );

  if (!Component) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-sm text-muted-foreground">
        Unsupported block: {block.name}
        {block.name in BLOCK_LABELS && ` (${BLOCK_LABELS[block.name]})`}
      </div>
    );
  }

  return (
    <Component
      block={block}
      attributes={block.attributes as Record<string, unknown>}
      isSelected={isSelected}
      onUpdate={handleUpdate}
    />
  );
}
