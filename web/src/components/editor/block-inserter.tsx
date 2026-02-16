"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Type, Layout, Image, List, Quote, Code, Columns, Minus, Grid } from "lucide-react";

interface BlockInserterProps {
  onInsertBlock: (blockType: string) => void;
  position?: "above" | "below";
}

const blockTypes = [
  {
    category: "Text",
    blocks: [
      { name: "core/paragraph", label: "Paragraph", icon: Type, description: "Start with basic text" },
      { name: "core/heading", label: "Heading", icon: Layout, description: "Section heading" },
      { name: "core/quote", label: "Quote", icon: Quote, description: "Blockquote citation" },
    ],
  },
  {
    category: "Media",
    blocks: [
      { name: "core/image", label: "Image", icon: Image, description: "Insert an image" },
    ],
  },
  {
    category: "Design",
    blocks: [
      { name: "core/list", label: "List", icon: List, description: "Bullet or numbered list" },
      { name: "core/code", label: "Code", icon: Code, description: "Code snippet" },
      { name: "core/separator", label: "Separator", icon: Minus, description: "Horizontal line" },
      { name: "core/spacer", label: "Spacer", icon: Grid, description: "Add vertical space" },
    ],
  },
  {
    category: "Layout",
    blocks: [
      { name: "core/columns", label: "Columns", icon: Columns, description: "Side by side blocks" },
      { name: "core/group", label: "Group", icon: Grid, description: "Group blocks together" },
    ],
  },
];

export function BlockInserter({ onInsertBlock, position = "below" }: BlockInserterProps) {
  const [open, setOpen] = useState(false);

  const handleInsert = (blockType: string) => {
    onInsertBlock(blockType);
    setOpen(false);
  };

  return (
    <div className={`flex justify-center ${position === "above" ? "mb-2" : "mt-2"}`}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 rounded-full opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity hover:bg-primary hover:text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="center">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold mb-2">Add Block</h4>
              <p className="text-xs text-muted-foreground">
                Choose a block to insert into your content
              </p>
            </div>
            <ScrollArea className="h-[400px]">
              <div className="space-y-4">
                {blockTypes.map((category) => (
                  <div key={category.category}>
                    <h5 className="text-xs font-medium text-muted-foreground mb-2">
                      {category.category}
                    </h5>
                    <div className="space-y-1">
                      {category.blocks.map((block) => {
                        const Icon = block.icon;
                        return (
                          <button
                            key={block.name}
                            onClick={() => handleInsert(block.name)}
                            className="w-full flex items-start gap-3 p-2 rounded-md hover:bg-accent text-left transition-colors"
                          >
                            <Icon className="h-5 w-5 mt-0.5 shrink-0 text-muted-foreground" />
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-sm">{block.label}</div>
                              <div className="text-xs text-muted-foreground">
                                {block.description}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
