"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import {
  FileText,
  Plus,
  Save,
  Settings,
  Keyboard,
  Layout,
  Type,
  Image,
  List,
  Quote,
  Code,
  Columns,
  File,
} from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreatePost?: () => void;
  onCreatePage?: () => void;
  onSave?: () => void;
  onOpenSettings?: () => void;
  onOpenShortcuts?: () => void;
}

export function CommandPalette({
  open,
  onOpenChange,
  onCreatePost,
  onCreatePage,
  onSave,
  onOpenSettings,
  onOpenShortcuts,
}: CommandPaletteProps) {
  const router = useRouter();
  const posts = usePostStore((s) => s.posts);
  const currentPost = usePostStore((s) => s.currentPost);
  const setCurrentPost = usePostStore((s) => s.setCurrentPost);
  const addBlock = useEditorStore((s) => s.addBlock);

  const runCommand = useCallback(
    (command: () => void) => {
      onOpenChange(false);
      command();
    },
    [onOpenChange]
  );

  // Block insertion commands
  const insertBlock = useCallback(
    (blockName: string) => {
      const blockDefaults: Record<string, any> = {
        "core/paragraph": { content: "" },
        "core/heading": { content: "", level: 2 },
        "core/image": { url: "", alt: "" },
        "core/list": { ordered: false, values: "" },
        "core/quote": { value: "", citation: "" },
        "core/code": { content: "" },
        "core/columns": { columns: 2 },
      };

      addBlock({
        clientId: `block-${Date.now()}-${Math.random()}`,
        name: blockName,
        attributes: blockDefaults[blockName] || {},
        innerBlocks: [],
      });
    },
    [addBlock]
  );

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Actions */}
        <CommandGroup heading="Actions">
          {onCreatePost && (
            <CommandItem onSelect={() => runCommand(onCreatePost)}>
              <Plus className="mr-2 h-4 w-4" />
              <span>Create New Post</span>
            </CommandItem>
          )}
          {onCreatePage && (
            <CommandItem onSelect={() => runCommand(onCreatePage)}>
              <File className="mr-2 h-4 w-4" />
              <span>Create New Page</span>
            </CommandItem>
          )}
          {onSave && currentPost && (
            <CommandItem onSelect={() => runCommand(onSave)}>
              <Save className="mr-2 h-4 w-4" />
              <span>Save Post</span>
              <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                <span className="text-xs">⌘</span>S
              </kbd>
            </CommandItem>
          )}
          {onOpenSettings && (
            <CommandItem onSelect={() => runCommand(onOpenSettings)}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Open Settings</span>
            </CommandItem>
          )}
          {onOpenShortcuts && (
            <CommandItem onSelect={() => runCommand(onOpenShortcuts)}>
              <Keyboard className="mr-2 h-4 w-4" />
              <span>Keyboard Shortcuts</span>
              <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                ?
              </kbd>
            </CommandItem>
          )}
        </CommandGroup>

        {/* Insert Block */}
        {currentPost && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Insert Block">
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/paragraph"))}>
                <Type className="mr-2 h-4 w-4" />
                <span>Paragraph</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/heading"))}>
                <Layout className="mr-2 h-4 w-4" />
                <span>Heading</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/image"))}>
                <Image className="mr-2 h-4 w-4" />
                <span>Image</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/list"))}>
                <List className="mr-2 h-4 w-4" />
                <span>List</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/quote"))}>
                <Quote className="mr-2 h-4 w-4" />
                <span>Quote</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/code"))}>
                <Code className="mr-2 h-4 w-4" />
                <span>Code</span>
              </CommandItem>
              <CommandItem onSelect={() => runCommand(() => insertBlock("core/columns"))}>
                <Columns className="mr-2 h-4 w-4" />
                <span>Columns</span>
              </CommandItem>
            </CommandGroup>
          </>
        )}

        {/* Recent Posts */}
        {posts.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Recent Posts">
              {posts.slice(0, 5).map((post) => (
                <CommandItem
                  key={post.id}
                  onSelect={() => {
                    runCommand(() => {
                      // This will be handled by parent component
                      window.dispatchEvent(
                        new CustomEvent("loadPost", { detail: { postId: post.id } })
                      );
                    });
                  }}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  <span>{post.title || "Untitled"}</span>
                  {currentPost?.id === post.id && (
                    <span className="ml-auto text-xs text-muted-foreground">Current</span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
