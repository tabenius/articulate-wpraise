"use client";

import { useState, useCallback, useRef } from "react";
import type { BlockProps, ImageAttributes } from "@/types/blocks";
import { ImageIcon, Upload } from "lucide-react";

export function ImageBlock({
  attributes,
  isSelected,
  onUpdate,
}: BlockProps<ImageAttributes>) {
  const [isEditing, setIsEditing] = useState(false);
  const [urlInput, setUrlInput] = useState(attributes.url || "");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("alt_text", attributes.alt || "");

      const uploadRes = await fetch("/api/media", {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        throw new Error("Failed to upload file");
      }

      const uploadData = await uploadRes.json();

      if (uploadData.error) {
        throw new Error(uploadData.error);
      }

      onUpdate({
        url: uploadData.url,
        alt: attributes.alt || "",
        width: uploadData.width,
        height: uploadData.height,
      });
      setIsEditing(false);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to upload file");
    } finally {
      setUploading(false);
    }
  }, [attributes.alt, onUpdate]);

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
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />

        <div className="flex flex-col gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full px-3 py-3 border-2 border-dashed rounded-md text-sm bg-background hover:bg-accent flex items-center justify-center gap-2"
          >
            <Upload className="h-4 w-4" />
            {uploading ? "Uploading..." : "Choose Image File"}
          </button>

          <div className="relative flex items-center">
            <div className="flex-grow border-t border-border"></div>
            <span className="mx-2 text-xs text-muted-foreground">or</span>
            <div className="flex-grow border-t border-border"></div>
          </div>
        </div>

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
            disabled={uploading}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md disabled:opacity-50"
          >
            Save URL
          </button>
          <button
            onClick={() => setIsEditing(false)}
            disabled={uploading}
            className="px-3 py-1.5 text-sm border rounded-md disabled:opacity-50"
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
