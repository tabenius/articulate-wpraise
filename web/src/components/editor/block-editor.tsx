"use client";

import { useCallback } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useEditorStore } from "@/stores/editor-store";
import { BlockWrapper } from "./block-wrapper";
import { FeaturedImagePanel } from "./featured-image-panel";
import { TaxonomyPanel } from "./taxonomy-panel";
import { PublishPanel } from "./publish-panel";

export function BlockEditor() {
  const blocks = useEditorStore((s) => s.blocks);
  const moveBlock = useEditorStore((s) => s.moveBlock);
  const selectBlock = useEditorStore((s) => s.selectBlock);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const newIndex = blocks.findIndex((b) => b.clientId === over.id);
      moveBlock(active.id as string, newIndex);
    },
    [blocks, moveBlock]
  );

  const handleBackgroundClick = useCallback(() => {
    selectBlock(null);
  }, [selectBlock]);

  if (blocks.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-lg mb-2">No blocks yet</p>
          <p className="text-sm">
            Use the &quot;Add Block&quot; button or ask the AI to create content
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="pl-12 pr-4 py-4" onClick={handleBackgroundClick}>
      <div className="max-w-3xl mx-auto">
        <PublishPanel />
        <FeaturedImagePanel />
        <TaxonomyPanel />
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={blocks.map((b) => b.clientId)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-1">
              {blocks.map((block) => (
                <BlockWrapper key={block.clientId} block={block} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}
