"use client";

import { useCallback } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEditorStore } from "@/stores/editor-store";
import { BlockRenderer } from "./block-renderer";
import { Badge } from "@/components/ui/badge";
import { BLOCK_LABELS } from "@/types/blocks";
import { GripVertical, Trash2 } from "lucide-react";
import type { Block } from "@/types/blocks";

interface BlockWrapperProps {
  block: Block;
}

export function BlockWrapper({ block }: BlockWrapperProps) {
  const selectedBlockId = useEditorStore((s) => s.selectedBlockId);
  const selectBlock = useEditorStore((s) => s.selectBlock);
  const removeBlock = useEditorStore((s) => s.removeBlock);

  const isSelected = selectedBlockId === block.clientId;

  const {
    attributes: dndAttributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: block.clientId });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      selectBlock(block.clientId);
    },
    [block.clientId, selectBlock]
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      removeBlock(block.clientId);
    },
    [block.clientId, removeBlock]
  );

  const label = BLOCK_LABELS[block.name] || block.name.split("/").pop() || "Block";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`block-wrapper group relative rounded-lg transition-all ${
        isSelected
          ? "bg-accent/50 shadow-sm"
          : "hover:bg-accent/30"
      }`}
      onClick={handleClick}
    >
      {/* Block controls - visible on hover/select */}
      <div
        className={`block-controls absolute -left-10 top-0 flex flex-col items-center gap-1 transition-opacity ${
          isSelected ? "opacity-100" : "opacity-0"
        }`}
      >
        <button
          className="p-1 rounded hover:bg-accent cursor-grab active:cursor-grabbing"
          {...dndAttributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground" />
        </button>
        <button
          onClick={handleDelete}
          className="p-1 rounded hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Block type badge */}
      {isSelected && (
        <div className="absolute -top-3 left-2 z-10">
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {label}
          </Badge>
        </div>
      )}

      {/* Block content */}
      <div className="px-3 py-2">
        <BlockRenderer block={block} />
      </div>
    </div>
  );
}
