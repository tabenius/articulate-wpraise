"use client";

import { useCallback, useState } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { Button } from "@/components/ui/button";
import { BLOCK_LABELS } from "@/types/blocks";
import type { Block } from "@/types/blocks";
import {
  Plus,
  Type,
  Heading,
  Image,
  List,
  Quote,
  Code,
  Columns,
  Minus,
  Square,
} from "lucide-react";

const INSERTABLE_BLOCKS = [
  { name: "core/paragraph", icon: Type, label: "Paragraph" },
  { name: "core/heading", icon: Heading, label: "Heading" },
  { name: "core/image", icon: Image, label: "Image" },
  { name: "core/list", icon: List, label: "List" },
  { name: "core/quote", icon: Quote, label: "Quote" },
  { name: "core/code", icon: Code, label: "Code" },
  { name: "core/columns", icon: Columns, label: "Columns" },
  { name: "core/separator", icon: Minus, label: "Separator" },
  { name: "core/spacer", icon: Square, label: "Spacer" },
] as const;

const DEFAULT_ATTRIBUTES: Record<string, Record<string, unknown>> = {
  "core/paragraph": { content: "" },
  "core/heading": { content: "", level: 2 },
  "core/image": { url: "", alt: "" },
  "core/list": { ordered: false, values: "<li></li>" },
  "core/quote": { value: "", citation: "" },
  "core/code": { content: "" },
  "core/columns": {},
  "core/separator": {},
  "core/spacer": { height: "50px" },
};

export function BlockToolbar() {
  const [isOpen, setIsOpen] = useState(false);
  const addBlock = useEditorStore((s) => s.addBlock);

  const handleInsert = useCallback(
    (blockName: string) => {
      const block: Block = {
        name: blockName,
        clientId: crypto.randomUUID(),
        attributes: DEFAULT_ATTRIBUTES[blockName] || {},
        innerBlocks: [],
      };

      // Add inner blocks for columns
      if (blockName === "core/columns") {
        block.innerBlocks = [
          {
            name: "core/column",
            clientId: crypto.randomUUID(),
            attributes: {},
            innerBlocks: [],
          },
          {
            name: "core/column",
            clientId: crypto.randomUUID(),
            attributes: {},
            innerBlocks: [],
          },
        ];
      }

      addBlock(block);
      setIsOpen(false);
    },
    [addBlock]
  );

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="gap-1"
      >
        <Plus className="h-4 w-4" />
        Add Block
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 z-50 bg-background border rounded-lg shadow-lg p-2 grid grid-cols-3 gap-1 w-64">
            {INSERTABLE_BLOCKS.map(({ name, icon: Icon, label }) => (
              <button
                key={name}
                onClick={() => handleInsert(name)}
                className="flex flex-col items-center gap-1 p-2 rounded-md hover:bg-accent text-sm transition-colors"
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{label}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
