/**
 * Frontend API client helpers for communicating with Next.js API routes.
 */

import type { Post, PostSummary } from "@/types/post";
import type { Block } from "@/types/blocks";
import type { CreatePostResponse, UpdatePostResponse, GetPostResponse } from "@/types/mcp-generated";
import { logger } from "./logger";
import { getErrorMessage } from "./api-contract";

const API_BASE = "/api";
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2;
const POSTS_CACHE_KEY = "wpai:last_posts";
const POST_CACHE_PREFIX = "wpai:last_post:";

function createRequestId(): string {
  return crypto.randomUUID();
}

async function fetchJSON<T>(
  url: string,
  options?: RequestInit,
  timeout: number = DEFAULT_TIMEOUT,
  retries: number = MAX_RETRIES
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const method = (options?.method || "GET").toUpperCase();
    const isMutation = method !== "GET";
    const requestId = createRequestId();
    const headers = {
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
      ...(isMutation ? { "Idempotency-Key": requestId } : {}),
      ...(options?.headers || {}),
    };
    const response = await fetch(`${API_BASE}${url}`, {
      headers,
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorPayload: unknown = null;
      try {
        errorPayload = await response.json();
      } catch {
        // fallback to plain text
        try {
          const errorText = await response.text();
          throw new Error(errorText || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }
      throw new Error(getErrorMessage(errorPayload) || `HTTP ${response.status}`);
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
  try {
    const envelope = await fetchJSON<{ data?: PostSummary[] }>("/posts");
    const result = envelope?.data ?? [];
    if (!Array.isArray(result)) {
      logger.error("fetchPosts returned non-array:", result);
      throw new Error("Invalid post list response");
    }
    if (typeof window !== "undefined") {
      localStorage.setItem(POSTS_CACHE_KEY, JSON.stringify(result));
    }
    return result;
  } catch (error) {
    if (typeof window !== "undefined") {
      const cached = localStorage.getItem(POSTS_CACHE_KEY);
      if (cached) {
        try {
          const parsed = JSON.parse(cached) as PostSummary[];
          logger.warn("Using cached posts due to fetch failure");
          return parsed;
        } catch {
          // ignore bad cache
        }
      }
    }
    throw error;
  }
}

export async function fetchPost(id: number, type: string = "post"): Promise<Post> {
  if (!id || typeof id !== "number" || id <= 0) {
    throw new Error(`Invalid post ID: ${id}`);
  }
  const query = type === "page" ? "?type=page" : "";
  const envelope = await fetchJSON<{ data?: Post }>(`/posts/${id}${query}`);
  const result = envelope?.data as Post;
  // Validate required fields
  if (!result || typeof result.id !== "number") {
    throw new Error("Invalid post data received from server");
  }
  if (typeof window !== "undefined") {
    localStorage.setItem(`${POST_CACHE_PREFIX}${id}`, JSON.stringify(result));
  }
  return result;
}

export async function createPost(title: string): Promise<Post> {
  // Validate input
  if (!title || typeof title !== "string") {
    throw new Error("Invalid title: must be a non-empty string");
  }

  const envelope = await fetchJSON<{ data?: CreatePostResponse }>("/posts", {
    method: "POST",
    body: JSON.stringify({ title: title.trim(), status: "draft" }),
  });
  const result = envelope?.data as CreatePostResponse;
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

  const envelope = await fetchJSON<{ data?: CreatePostResponse }>("/posts", {
    method: "POST",
    body: JSON.stringify({ title: title.trim(), status: "draft", type: "page" }),
  });
  const result = envelope?.data as CreatePostResponse;
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
  const envelope = await fetchJSON<{ data?: Post }>(`/posts/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  const result = envelope?.data as Post;
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
  const envelope = await fetchJSON<{ data?: Block[] }>(`/blocks?postId=${postId}`);
  const result = envelope?.data ?? [];
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
  const envelope = await fetchJSON<{ data?: { success: boolean } }>("/blocks", {
    method: "PUT",
    body: JSON.stringify({ postId, blocks }),
  });
  return envelope?.data ?? { success: false };
}

// Media
export async function fetchMedia(): Promise<
  Array<{ id: number; url: string; title: string; alt: string }>
> {
  return fetchJSON("/media");
}
