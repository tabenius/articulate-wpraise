/**
 * Frontend API client helpers for communicating with Next.js API routes.
 */

import type { Post, PostSummary } from "@/types/post";
import type { Block } from "@/types/blocks";
import type { CreatePostResponse, UpdatePostResponse, GetPostResponse } from "@/types/mcp-generated";
import { logger } from "./logger";

const API_BASE = "/api";
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2;

async function fetchJSON<T>(
  url: string,
  options?: RequestInit,
  timeout: number = DEFAULT_TIMEOUT,
  retries: number = MAX_RETRIES
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorText: string;
      try {
        errorText = await response.text();
      } catch {
        errorText = `HTTP ${response.status}`;
      }
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    // Safely parse JSON with error handling
    try {
      const data = await response.json();
      return data as T;
    } catch (error) {
      throw new Error(
        `Invalid JSON response: ${error instanceof Error ? error.message : "unknown error"}`
      );
    }
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle abort/timeout
    if (error instanceof Error && error.name === "AbortError") {
      if (retries > 0) {
        logger.warn(`Request timeout, retrying... (${retries} retries left)`);
        return fetchJSON<T>(url, options, timeout, retries - 1);
      }
      throw new Error("Request timeout - please check your connection");
    }

    // Handle network errors with retry
    if (
      error instanceof TypeError &&
      error.message.includes("fetch") &&
      retries > 0
    ) {
      logger.warn(`Network error, retrying... (${retries} retries left)`);
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Wait 1s before retry
      return fetchJSON<T>(url, options, timeout, retries - 1);
    }

    throw error;
  }
}

// Posts
export async function fetchPosts(): Promise<PostSummary[]> {
  const result = await fetchJSON<PostSummary[]>("/posts");
  // Validate response is an array
  if (!Array.isArray(result)) {
    logger.error("fetchPosts returned non-array:", result);
    return [];
  }
  return result;
}

export async function fetchPost(id: number, type: string = "post"): Promise<Post> {
  if (!id || typeof id !== "number" || id <= 0) {
    throw new Error(`Invalid post ID: ${id}`);
  }
  const query = type === "page" ? "?type=page" : "";
  const result = await fetchJSON<Post>(`/posts/${id}${query}`);
  // Validate required fields
  if (!result || typeof result.id !== "number") {
    throw new Error("Invalid post data received from server");
  }
  return result;
}

export async function createPost(title: string): Promise<Post> {
  // Validate input
  if (!title || typeof title !== "string") {
    throw new Error("Invalid title: must be a non-empty string");
  }

  const result = await fetchJSON<CreatePostResponse>("/posts", {
    method: "POST",
    body: JSON.stringify({ title: title.trim(), status: "draft" }),
  });
  logger.info("createPost API response:", result);

  // Runtime validation - ensure id exists
  if (!result || typeof result.id !== "number" || result.id <= 0) {
    logger.error("Invalid response structure:", result);
    throw new Error(
      `Invalid response from create_post: missing or invalid id field. Got: ${JSON.stringify(result)}`
    );
  }

  // Ensure required fields exist
  if (!result.title) {
    result.title = title;
  }

  return result as Post;
}

export async function createPage(title: string): Promise<Post> {
  // Validate input
  if (!title || typeof title !== "string") {
    throw new Error("Invalid title: must be a non-empty string");
  }

  const result = await fetchJSON<CreatePostResponse>("/posts", {
    method: "POST",
    body: JSON.stringify({ title: title.trim(), status: "draft", type: "page" }),
  });
  logger.info("createPage API response:", result);

  // Runtime validation - ensure id exists
  if (!result || typeof result.id !== "number" || result.id <= 0) {
    logger.error("Invalid response structure:", result);
    throw new Error(
      `Invalid response from create_post: missing or invalid id field. Got: ${JSON.stringify(result)}`
    );
  }

  // Ensure required fields exist
  if (!result.title) {
    result.title = title;
  }

  return result as Post;
}

export async function updatePost(
  id: number,
  data: Partial<Post>
): Promise<Post> {
  if (!id || typeof id !== "number" || id <= 0) {
    throw new Error(`Invalid post ID: ${id}`);
  }
  if (!data || typeof data !== "object") {
    throw new Error("Invalid post data: must be an object");
  }
  const result = await fetchJSON<Post>(`/posts/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  // Validate required fields
  if (!result || typeof result.id !== "number") {
    throw new Error("Invalid post data received from server");
  }
  return result;
}

// Blocks
export async function fetchBlocks(postId: number): Promise<Block[]> {
  if (!postId || typeof postId !== "number" || postId <= 0) {
    throw new Error(`Invalid post ID: ${postId}`);
  }
  const result = await fetchJSON<Block[]>(`/blocks?postId=${postId}`);
  // Validate response is an array
  if (!Array.isArray(result)) {
    logger.error("fetchBlocks returned non-array:", result);
    return [];
  }
  return result;
}

export async function saveBlocks(
  postId: number,
  blocks: Block[]
): Promise<{ success: boolean }> {
  if (!postId || typeof postId !== "number" || postId <= 0) {
    throw new Error(`Invalid post ID: ${postId}`);
  }
  if (!Array.isArray(blocks)) {
    throw new Error("Invalid blocks: must be an array");
  }
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
