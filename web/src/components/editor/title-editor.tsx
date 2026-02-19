"use client";

import { useState, useEffect } from "react";
import { usePostStore } from "@/stores/post-store";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { updatePost } from "@/lib/api";

export function TitleEditor() {
  const currentPost = usePostStore((s) => s.currentPost);
  const updatePostInStore = usePostStore((s) => s.updatePost);
  const { toast } = useToast();

  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);

  // Sync title with current post
  useEffect(() => {
    if (currentPost) {
      setTitle(currentPost.title || "");
    }
  }, [currentPost]);

  const handleSaveTitle = async () => {
    if (!currentPost || title === currentPost.title) return;

    setSaving(true);
    try {
      const updatedPost = await updatePost(currentPost.id, { title });
      updatePostInStore(currentPost.id, updatedPost);
    } catch (error) {
      console.error("Failed to save title:", error);
      toast({
        variant: "destructive",
        title: "Error saving title",
        description: error instanceof Error ? error.message : "Failed to save",
      });
      // Revert to original title on error
      setTitle(currentPost.title || "");
    } finally {
      setSaving(false);
    }
  };

  if (!currentPost) {
    return (
      <div className="px-4 py-6">
        <div className="text-muted-foreground text-center">
          No post selected. Create a new post or load an existing one.
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 border-b">
      <Input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={handleSaveTitle}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleSaveTitle();
          }
        }}
        placeholder="Enter post title..."
        className="text-4xl font-bold border-none focus-visible:ring-0 px-0 h-auto"
        disabled={saving}
      />
      {saving && (
        <div className="text-xs text-muted-foreground mt-1">Saving title...</div>
      )}
    </div>
  );
}
