"use client";

import { useEffect, useState } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { useTemplateStore } from "@/stores/template-store";
import { BlockEditor } from "@/components/editor/block-editor";
import { SplitView } from "@/components/layout/split-view";
import { TemplatePreview } from "./template-preview";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Save, Eye, Code2, Blocks, Columns2, Check, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { parseBlocks, serializeBlocks } from "@/lib/block-serializer";
import type { Block } from "@/types/blocks";

interface TemplateEditorProps {
  templateId: number;
  type: "template" | "part";
  onSave?: () => void;
}

export function TemplateEditor({ templateId, type, onSave }: TemplateEditorProps) {
  const [viewMode, setViewMode] = useState<"visual" | "code">("visual");
  const [layoutMode, setLayoutMode] = useState<"editor" | "split" | "preview">("editor");
  const [isSaving, setIsSaving] = useState(false);
  const [content, setContent] = useState<string>("");
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const currentTemplate = useTemplateStore((s: any) => s.currentTemplate);
  const templateParts = useTemplateStore((s: any) => s.templateParts);
  const updateTemplate = useTemplateStore((s: any) => s.updateTemplate);
  const blocks = useEditorStore((s: any) => s.blocks);
  const setBlocks = useEditorStore((s: any) => s.setBlocks);
  const isDirty = useEditorStore((s: any) => s.isDirty);
  const setDirty = useEditorStore((s: any) => s.setDirty);
  const { toast } = useToast();

  // Get the current item (template or template part)
  const currentItem = type === "template"
    ? currentTemplate
    : templateParts.find((p: any) => p.id === templateId);

  // Format time since last save
  const formatTimeSince = (date: Date) => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  // Load template or template part content into block editor
  useEffect(() => {
    if (!currentItem) return;

    try {
      // Parse WordPress blocks from HTML comment format
      const parsedBlocks = parseBlocks(currentItem.content || "");

      // If no blocks found, treat as raw HTML
      if (parsedBlocks.length === 0 && currentItem.content) {
        const fallbackBlock: Block = {
          clientId: `${type}-block-${Date.now()}`,
          name: "core/html",
          attributes: {
            content: currentItem.content,
          },
          innerBlocks: [],
        };
        setBlocks([fallbackBlock]);
      } else {
        setBlocks(parsedBlocks);
      }

      console.log(`Parsed ${parsedBlocks.length} blocks from ${type}`);
      setContent(currentItem.content || "");
    } catch (error) {
      console.error(`Failed to parse ${type} blocks:`, error);
      toast({
        variant: "destructive",
        title: `Error loading ${type}`,
        description: `Failed to parse ${type} content`,
      });
    }
  }, [currentItem, type, setBlocks, toast]);

  const handleSave = async () => {
    if (!currentItem) return;

    try {
      setIsSaving(true);

      // Serialize blocks back to WordPress block comment format
      const content = serializeBlocks(blocks);

      // Use the correct API endpoint based on type
      const endpoint = type === "template"
        ? `/api/templates/${currentItem.id}`
        : `/api/template-parts/${currentItem.id}`;

      const response = await fetch(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      // Update store based on type
      if (type === "template") {
        updateTemplate(currentItem.id, { content });
      }
      // Note: For template parts, we would need a similar updateTemplatePart function in the store

      setDirty(false);
      setLastSaved(new Date());

      toast({
        title: `${type === "template" ? "Template" : "Template part"} saved`,
        description: `"${currentItem.title}" has been saved to WordPress`,
      });

      console.log(`Saved ${blocks.length} blocks to ${type}`);
      onSave?.();
    } catch (error) {
      console.error(`Failed to save ${type}:`, error);
      toast({
        variant: "destructive",
        title: `Error saving ${type}`,
        description:
          error instanceof Error ? error.message : `Failed to save ${type}`,
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (!currentItem) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        No {type} selected
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="border-b bg-muted/20 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">{currentItem.title}</h2>
          <span className="text-xs text-muted-foreground">
            {currentItem.slug}
          </span>
          {/* Save status indicator */}
          {isSaving ? (
            <span className="text-xs flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3 w-3 animate-spin" />
              Saving...
            </span>
          ) : isDirty ? (
            <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded">
              Unsaved changes
            </span>
          ) : lastSaved ? (
            <span className="text-xs flex items-center gap-1 text-green-600 dark:text-green-400">
              <Check className="h-3 w-3" />
              Saved {formatTimeSince(lastSaved)}
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 border rounded-md p-1">
            <Button
              variant={viewMode === "visual" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("visual")}
              className="h-7"
            >
              <Blocks className="h-4 w-4 mr-1" />
              Visual
            </Button>
            <Button
              variant={viewMode === "code" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("code")}
              className="h-7"
            >
              <Code2 className="h-4 w-4 mr-1" />
              Code
            </Button>
          </div>

          {/* Layout Mode Toggle */}
          <div className="flex items-center gap-1 border rounded-md p-1">
            <Button
              variant={layoutMode === "editor" ? "default" : "ghost"}
              size="sm"
              onClick={() => setLayoutMode("editor")}
              className="h-7"
              title="Editor only"
            >
              <Blocks className="h-4 w-4" />
            </Button>
            <Button
              variant={layoutMode === "split" ? "default" : "ghost"}
              size="sm"
              onClick={() => setLayoutMode("split")}
              className="h-7"
              title="Split view"
            >
              <Columns2 className="h-4 w-4" />
            </Button>
            <Button
              variant={layoutMode === "preview" ? "default" : "ghost"}
              size="sm"
              onClick={() => setLayoutMode("preview")}
              className="h-7"
              title="Preview only"
            >
              <Eye className="h-4 w-4" />
            </Button>
          </div>

          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isDirty || isSaving}
          >
            <Save className="h-4 w-4 mr-1" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      {/* Editor Content */}
      {layoutMode === "preview" ? (
        <TemplatePreview templateId={currentItem.id} />
      ) : layoutMode === "split" ? (
        <SplitView
          left={
            viewMode === "visual" ? (
              <ScrollArea className="h-full">
                <BlockEditor />
              </ScrollArea>
            ) : (
              <ScrollArea className="h-full">
                <div className="p-8">
                  <textarea
                    className="w-full min-h-[600px] font-mono text-sm bg-muted/30 rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-ring"
                    value={currentItem.content || ""}
                    onChange={(e) => {
                      if (type === "template") {
                        updateTemplate(currentItem.id, {
                          content: e.target.value,
                        });
                      }
                      setDirty(true);
                    }}
                    placeholder={`${type === "template" ? "Template" : "Template part"} HTML...`}
                  />
                </div>
              </ScrollArea>
            )
          }
          right={<TemplatePreview templateId={currentItem.id} />}
          defaultSize={50}
          leftId="template-editor"
          rightId="template-preview"
        />
      ) : viewMode === "visual" ? (
        <ScrollArea className="flex-1">
          <BlockEditor />
        </ScrollArea>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-8 max-w-4xl mx-auto">
            <textarea
              className="w-full min-h-[600px] font-mono text-sm bg-muted/30 rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-ring"
              value={currentItem.content || ""}
              onChange={(e) => {
                if (type === "template") {
                  updateTemplate(currentItem.id, {
                    content: e.target.value,
                  });
                }
                setDirty(true);
              }}
              placeholder={`${type === "template" ? "Template" : "Template part"} HTML...`}
            />
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
