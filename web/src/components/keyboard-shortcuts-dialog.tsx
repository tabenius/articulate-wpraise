"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

interface KeyboardShortcutsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KeyboardShortcutsDialog({
  open,
  onOpenChange,
}: KeyboardShortcutsDialogProps) {
  const [isMac, setIsMac] = useState(false);

  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().indexOf("MAC") >= 0);
  }, []);

  const mod = isMac ? "⌘" : "Ctrl";

  const shortcuts = [
    {
      category: "Editor",
      items: [
        { keys: [`${mod}`, "Z"], description: "Undo" },
        { keys: [`${mod}`, "Shift", "Z"], description: "Redo" },
        { keys: [isMac ? "^" : "Ctrl", "Y"], description: "Redo (alternative)" },
        { keys: [`${mod}`, "S"], description: "Save post" },
        { keys: ["Esc"], description: "Deselect block" },
      ],
    },
    {
      category: "Navigation",
      items: [
        { keys: ["?"], description: "Show keyboard shortcuts" },
        { keys: [`${mod}`, "K"], description: "Command palette (coming soon)" },
      ],
    },
    {
      category: "Chat",
      items: [
        { keys: ["Enter"], description: "Send message" },
        { keys: ["Shift", "Enter"], description: "New line in message" },
      ],
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Speed up your workflow with these keyboard shortcuts
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {shortcuts.map((category) => (
            <div key={category.category}>
              <h3 className="text-sm font-semibold mb-3">{category.category}</h3>
              <div className="space-y-2">
                {category.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between py-2"
                  >
                    <span className="text-sm text-muted-foreground">
                      {item.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((key, keyIdx) => (
                        <span key={keyIdx} className="flex items-center gap-1">
                          <kbd className="pointer-events-none inline-flex h-7 select-none items-center gap-1 rounded border bg-muted px-2 font-mono text-sm font-medium text-muted-foreground">
                            {key}
                          </kbd>
                          {keyIdx < item.keys.length - 1 && (
                            <span className="text-muted-foreground">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {category.category !== shortcuts[shortcuts.length - 1].category && (
                <Separator className="mt-4" />
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 p-4 bg-muted/50 rounded-lg">
          <p className="text-xs text-muted-foreground">
            <strong>Tip:</strong> Press <kbd className="px-1.5 py-0.5 rounded border bg-background font-mono text-xs">?</kbd> anytime to open this dialog.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
