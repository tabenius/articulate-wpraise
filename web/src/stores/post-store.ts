import { create } from "zustand";
import type { Post, PostSummary } from "@/types/post";

interface PostState {
  currentPost: Post | null;
  posts: PostSummary[];
  isLoading: boolean;
  error: string | null;

  setCurrentPost: (post: Post | null) => void;
  setPosts: (posts: PostSummary[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updatePost: (postId: number, updates: Partial<Post>) => void;
}

export const usePostStore = create<PostState>((set) => ({
  currentPost: null,
  posts: [],
  isLoading: false,
  error: null,

  setCurrentPost: (post) => set({ currentPost: post, error: null }),
  setPosts: (posts) => set({ posts }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  updatePost: (postId, updates) =>
    set((state) => ({
      currentPost:
        state.currentPost?.id === postId
          ? { ...state.currentPost, ...updates }
          : state.currentPost,
      posts: state.posts.map((post) =>
        post.id === postId ? { ...post, ...updates } : post
      ),
    })),
}));
