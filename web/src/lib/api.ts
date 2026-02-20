/**
 * Frontend API client helpers for communicating with Next.js API routes.
 */

import type { Post, PostSummary } from "@/types/post";
import type { Block } from "@/types/blocks";
import type { CreatePostResponse, UpdatePostResponse, GetPostResponse } from "@/types/mcp-generated";

const API_BASE = "/api";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
}

// Posts
export async function fetchPosts(): Promise<PostSummary[]> {
  return fetchJSON<PostSummary[]>("/posts");
}

export async function fetchPost(id: number): Promise<Post> {
  return fetchJSON<Post>(`/posts/${id}`);
}

export async function createPost(title: string): Promise<Post> {
  const result = await fetchJSON<CreatePostResponse>("/posts", {
    method: "POST",
    body: JSON.stringify({ title, status: "draft" }),
  });
  console.error("=== createPost API response ===", JSON.stringify(result, null, 2));

  // Runtime validation - ensure id exists
  if (!result || typeof result.id !== 'number') {
    console.error("=== ERROR: Invalid response structure ===", result);
    throw new Error(`Invalid response from create_post: missing or invalid id field. Got: ${JSON.stringify(result)}`);
  }

  return result as Post;
}

export async function createPage(title: string): Promise<Post> {
  const result = await fetchJSON<CreatePostResponse>("/posts", {
    method: "POST",
    body: JSON.stringify({ title, status: "draft", type: "page" }),
  });
  console.error("=== createPage API response ===", JSON.stringify(result, null, 2));

  // Runtime validation - ensure id exists
  if (!result || typeof result.id !== 'number') {
    console.error("=== ERROR: Invalid response structure ===", result);
    throw new Error(`Invalid response from create_post: missing or invalid id field. Got: ${JSON.stringify(result)}`);
  }

  return result as Post;
}

export async function updatePost(
  id: number,
  data: Partial<Post>
): Promise<Post> {
  return fetchJSON<Post>(`/posts/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// Blocks
export async function fetchBlocks(postId: number): Promise<Block[]> {
  return fetchJSON<Block[]>(`/blocks?postId=${postId}`);
}

export async function saveBlocks(
  postId: number,
  blocks: Block[]
): Promise<{ success: boolean }> {
  return fetchJSON<{ success: boolean }>("/blocks", {
    method: "PUT",
    body: JSON.stringify({ postId, blocks }),
  });
}

// Media
export async function fetchMedia(): Promise<
  Array<{ id: number; url: string; title: string; alt: string }>
> {
  return fetchJSON("/media");
}
