"use client";

import { useCallback, useEffect } from "react";
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
import { BlockInserter } from "./block-inserter";

export function BlockEditor() {
  const blocks = useEditorStore((s) => s.blocks);
  const moveBlock = useEditorStore((s) => s.moveBlock);
  const selectBlock = useEditorStore((s) => s.selectBlock);
  const addBlock = useEditorStore((s) => s.addBlock);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Add keyboard shortcuts for undo/redo and escape to deselect
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for Cmd (Mac) or Ctrl (Windows/Linux)
      const isMod = e.metaKey || e.ctrlKey;

      // Escape: Deselect current block
      if (e.key === "Escape") {
        e.preventDefault();
        selectBlock(null);
      }

      // Undo: Cmd+Z or Ctrl+Z
      if (isMod && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      }

      // Redo: Cmd+Shift+Z or Ctrl+Y or Ctrl+Shift+Z
      if ((isMod && e.shiftKey && e.key === "z") || (e.ctrlKey && e.key === "y")) {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [undo, redo, selectBlock]);

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

  const handleInsertBlock = useCallback(
    (blockType: string, index?: number) => {
      const blockDefaults: Record<string, any> = {
        "core/paragraph": { content: "" },
        "core/heading": { content: "", level: 2 },
        "core/image": { url: "", alt: "" },
        "core/list": { ordered: false, values: "" },
        "core/quote": { value: "", citation: "" },
        "core/code": { content: "" },
        "core/separator": {},
        "core/spacer": { height: 50 },
        "core/columns": { columns: 2 },
        "core/group": {},
      };

      addBlock(
        {
          clientId: `block-${Date.now()}-${Math.random()}`,
          name: blockType,
          attributes: blockDefaults[blockType] || {},
          innerBlocks: [],
        },
        index
      );
    },
    [addBlock]
  );

  if (blocks.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground px-4">
        <div className="text-center max-w-md">
          <div className="mb-4">
            <svg
              className="mx-auto h-16 w-16 text-muted-foreground/40"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No content yet
          </h3>
          <p className="text-sm mb-6">
            Start writing or use AI to create content. Use the &quot;Add Block&quot; button above or ask the AI assistant in the chat panel.
          </p>
          <div className="flex flex-col gap-2 text-xs text-left bg-muted/50 rounded-lg p-4">
            <p className="font-medium text-foreground mb-1">Try asking:</p>
            <p className="text-muted-foreground">
              💬 &quot;Write an introduction about...&quot;
            </p>
            <p className="text-muted-foreground">
              💬 &quot;Add a heading that says...&quot;
            </p>
            <p className="text-muted-foreground">
              💬 &quot;Create a list of...&quot;
            </p>
          </div>
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
              {blocks.map((block, index) => (
                <div key={block.clientId} className="group relative">
                  <BlockWrapper block={block} />
                  <BlockInserter
                    onInsertBlock={(type) => handleInsertBlock(type, index + 1)}
                    position="below"
                  />
                </div>
              ))}
            </div>
          </SortableContext>
        </DndContext>

        {/* Add block inserter at the end if no blocks */}
        {blocks.length === 0 && (
          <div className="mt-8">
            <BlockInserter onInsertBlock={(type) => handleInsertBlock(type)} />
          </div>
        )}
      </div>
    </div>
  );
}
