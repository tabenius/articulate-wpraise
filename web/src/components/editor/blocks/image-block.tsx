"use client";

import { useState, useCallback } from "react";
import type { BlockProps, ImageAttributes } from "@/types/blocks";
import { ImageIcon } from "lucide-react";

export function ImageBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ImageAttributes>) {
  const [isEditing, setIsEditing] = useState(false);
  const [urlInput, setUrlInput] = useState(attributes.url || "");

  const handleSave = useCallback(() => {
    onUpdate({ url: urlInput });
    setIsEditing(false);
  }, [urlInput, onUpdate]);

  if (!attributes.url && !isEditing) {
    return (
      <div
        className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-primary/50 transition-colors ${
          isSelected ? "border-primary" : "border-border"
        }`}
        onClick={() => setIsEditing(true)}
      >
        <ImageIcon className="h-8 w-8 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Click to add image URL</span>
      </div>
    );
  }

  if (isEditing) {
    return (
      <div className="border rounded-lg p-4 space-y-3">
        <input
          type="url"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="Enter image URL..."
          className="w-full px-3 py-2 border rounded-md text-sm bg-background"
          autoFocus
        />
        <input
          type="text"
          value={attributes.alt || ""}
          onChange={(e) => onUpdate({ alt: e.target.value })}
          placeholder="Alt text..."
          className="w-full px-3 py-2 border rounded-md text-sm bg-background"
        />
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md"
          >
            Save
          </button>
          <button
            onClick={() => setIsEditing(false)}
            className="px-3 py-1.5 text-sm border rounded-md"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <figure
      className={`${isSelected ? "ring-2 ring-primary/20 rounded" : ""}`}
      onClick={() => isSelected && setIsEditing(true)}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={attributes.url}
        alt={attributes.alt || ""}
        className="max-w-full rounded"
        style={{
          width: attributes.width ? `${attributes.width}px` : undefined,
          height: attributes.height ? `${attributes.height}px` : undefined,
        }}
      />
      {attributes.caption && (
        <figcaption className="text-sm text-muted-foreground mt-2 text-center">
          {attributes.caption}
        </figcaption>
      )}
    </figure>
  );
}
