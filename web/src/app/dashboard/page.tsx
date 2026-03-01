"use client";

import { useCallback, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { usePostStore } from "@/stores/post-store";
import { useEditorStore } from "@/stores/editor-store";
import { useBlocks } from "@/hooks/use-blocks";
import { useAutosave } from "@/hooks/use-autosave";
import { useSync } from "@/hooks/use-sync";
import { fetchPosts, fetchPost, createPost, createPage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function Home() {
  const setCurrentPost = usePostStore((s) => s.setCurrentPost);
  const setPosts = usePostStore((s) => s.setPosts);
  const setLoading = usePostStore((s) => s.setLoading);
  const setError = usePostStore((s) => s.setError);
  const { loadBlocks, persistBlocks } = useBlocks();
  const { toast } = useToast();

  // Enable autosave and chat<->editor sync
  useAutosave();
  useSync();

  const handleLoadPosts = useCallback(async () => {
    try {
      setLoading(true);
      const posts = await fetchPosts();
      setPosts(Array.isArray(posts) ? posts : []);
    } catch (error) {
      console.error("Failed to load posts:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to load posts";

      // Check if it's a 403 error (no WordPress connection)
      if (errorMessage.includes("403")) {
        // Try to auto-setup default connection
        try {
          const setupResponse = await fetch("/api/auth/setup-default-connection", {
            method: "POST",
          });

          const setupResult = await setupResponse.json();

          if (setupResult.success) {
            // Success! Retry loading posts
            toast({
              title: "WordPress connected!",
              description: "Your WordPress connection is ready.",
            });
            const posts = await fetchPosts();
            setPosts(Array.isArray(posts) ? posts : []);
            setLoading(false);
            return;
          } else if (setupResult.needsSetup) {
            // Auto-setup failed, redirect to manual setup
            window.location.href = "/setup";
            return;
          }
        } catch (setupError) {
          console.error("Auto-setup failed:", setupError);
          // Fallback to manual setup
          window.location.href = "/setup";
          return;
        }
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setPosts, setLoading, setError, toast]);

  // Load posts on mount
  useEffect(() => {
    handleLoadPosts();
  }, [handleLoadPosts]);

  const handleLoadPost = useCallback(
    async (postId: number, type?: string) => {
      try {
        setLoading(true);
        const post = await fetchPost(postId, type);
        setCurrentPost(post);
        await loadBlocks(postId);
        toast({
          title: "Post loaded",
          description: `Loaded "${post.title}"`,
        });
      } catch (error) {
        console.error("Failed to load post:", error);
        const errorMsg = error instanceof Error ? error.message : "Failed to load post";
        setError(errorMsg);
        toast({
          variant: "destructive",
          title: "Error loading post",
          description: errorMsg,
        });
      } finally {
        setLoading(false);
      }
    },
    [setCurrentPost, setLoading, setError, loadBlocks, toast]
  );

  const handleCreatePost = useCallback(async () => {
    try {
      setLoading(true);
      const post = await createPost("Untitled Post");
      console.log("handleCreatePost received post:", post);
      console.log("post.id:", post.id, "type:", typeof post.id);
      setCurrentPost(post);
      useEditorStore.getState().setBlocks([]);
      await handleLoadPosts();
      toast({
        variant: "success",
        title: "Post created",
        description: "New post ready to edit",
      });
    } catch (error) {
      console.error("Failed to create post:", error);
      const errorMsg = error instanceof Error ? error.message : "Failed to create post";
      setError(errorMsg);
      toast({
        variant: "destructive",
        title: "Error creating post",
        description: errorMsg,
      });
    } finally {
      setLoading(false);
    }
  }, [setCurrentPost, setLoading, setError, handleLoadPosts, toast]);

  const handleCreatePage = useCallback(async () => {
    try {
      setLoading(true);
      const page = await createPage("Untitled Page");
      console.log("handleCreatePage received page:", page);
      console.log("page.id:", page.id, "type:", typeof page.id);
      setCurrentPost(page);
      useEditorStore.getState().setBlocks([]);
      await handleLoadPosts();
      toast({
        variant: "success",
        title: "Page created",
        description: "New page ready to edit",
      });
    } catch (error) {
      console.error("Failed to create page:", error);
      const errorMsg = error instanceof Error ? error.message : "Failed to create page";
      setError(errorMsg);
      toast({
        variant: "destructive",
        title: "Error creating page",
        description: errorMsg,
      });
    } finally {
      setLoading(false);
    }
  }, [setCurrentPost, setLoading, setError, handleLoadPosts, toast]);

  const handleSave = useCallback(async () => {
    const currentPost = usePostStore.getState().currentPost;

    if (!currentPost) {
      toast({
        variant: "destructive",
        title: "No post loaded",
        description: "Please create or load a post before saving",
      });
      return;
    }

    try {
      await persistBlocks();
      toast({
        variant: "success",
        title: "Post saved",
        description: "All changes saved successfully",
      });
    } catch (error) {
      console.error("Failed to save:", error);
      toast({
        variant: "destructive",
        title: "Error saving post",
        description: error instanceof Error ? error.message : "Failed to save",
      });
    }
  }, [persistBlocks, toast]);

  return (
    <AppShell
      onLoadPost={handleLoadPost}
      onLoadPosts={handleLoadPosts}
      onSave={handleSave}
      onCreatePost={handleCreatePost}
      onCreatePage={handleCreatePage}
    />
  );
}
