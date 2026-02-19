import { useEffect, useRef } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { usePreviewStore } from "@/stores/preview-store";

/**
 * Hook to automatically fetch and update preview when blocks change
 * @param postId - WordPress post ID to preview
 * @param enabled - Whether preview fetching is enabled (e.g., only in split/preview mode)
 */
export function usePreview(postId: number | null, enabled: boolean = true) {
  const blocks = useEditorStore((s) => s.blocks);
  const { setHtml, setLoading, setError } = usePreviewStore();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Skip if preview is disabled or no post ID
    if (!enabled || !postId) {
      return;
    }

    // Clear any pending timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Debounce preview fetch by 1.5 seconds
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      setError(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch(`/api/preview/${postId}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          // Try to extract error message from response body
          let errorMessage = `Preview fetch failed: ${response.status}`;
          try {
            const errorData = await response.json();
            if (errorData.error) {
              errorMessage = errorData.error;
            }
          } catch {
            // If JSON parsing fails, use status text
            errorMessage = `${response.status} ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }

        const data = await response.json();

        if (data.error) {
          setError(data.error);
        } else if (data.success && data.html) {
          setHtml(data.html);
        } else {
          setError("Invalid preview response");
        }
      } catch (error) {
        // Ignore aborted requests
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }

        console.error("Preview fetch error:", error);
        setError(
          error instanceof Error ? error.message : "Failed to load preview"
        );
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }
    }, 1500); // 1.5s debounce

    // Cleanup on unmount or when dependencies change
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
    // Zustand actions (setHtml, setLoading, setError) are stable and excluded from deps
  }, [blocks, postId, enabled]); // eslint-disable-line react-hooks/exhaustive-deps
}
