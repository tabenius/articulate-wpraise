"use client";

import { useCallback, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { useBlocks } from "@/hooks/use-blocks";
import { useAutosave } from "@/hooks/use-autosave";
import { useSync } from "@/hooks/use-sync";
import { fetchPosts, fetchPost, createPost } from "@/lib/api";

export default function Home() {
  const setCurrentPost = usePostStore((s) => s.setCurrentPost);
  const setPosts = usePostStore((s) => s.setPosts);
  const setLoading = usePostStore((s) => s.setLoading);
  const setError = usePostStore((s) => s.setError);
  const { loadBlocks, persistBlocks } = useBlocks();

  // Enable autosave and chat<->editor sync
  useAutosave();
  useSync();

  // Load posts on mount
  useEffect(() => {
    handleLoadPosts();
  }, []);

  const handleLoadPosts = useCallback(async () => {
    try {
      setLoading(true);
      const posts = await fetchPosts();
      setPosts(Array.isArray(posts) ? posts : []);
    } catch (error) {
      console.error("Failed to load posts:", error);
      setError(error instanceof Error ? error.message : "Failed to load posts");
    } finally {
      setLoading(false);
    }
  }, [setPosts, setLoading, setError]);

  const handleLoadPost = useCallback(
    async (postId: number) => {
      try {
        setLoading(true);
        const post = await fetchPost(postId);
        setCurrentPost(post);
        await loadBlocks(postId);
      } catch (error) {
        console.error("Failed to load post:", error);
        setError(
          error instanceof Error ? error.message : "Failed to load post"
        );
      } finally {
        setLoading(false);
      }
    },
    [setCurrentPost, setLoading, setError, loadBlocks]
  );

  const handleCreatePost = useCallback(async () => {
    try {
      setLoading(true);
      const post = await createPost("Untitled Post");
      setCurrentPost(post);
      useEditorStore.getState().setBlocks([]);
      await handleLoadPosts();
    } catch (error) {
      console.error("Failed to create post:", error);
      setError(
        error instanceof Error ? error.message : "Failed to create post"
      );
    } finally {
      setLoading(false);
    }
  }, [setCurrentPost, setLoading, setError, handleLoadPosts]);

  const handleSave = useCallback(async () => {
    try {
      await persistBlocks();
    } catch (error) {
      console.error("Failed to save:", error);
    }
  }, [persistBlocks]);

  return (
    <AppShell
      onLoadPost={handleLoadPost}
      onLoadPosts={handleLoadPosts}
      onSave={handleSave}
      onCreatePost={handleCreatePost}
    />
  );
}
