import { create } from "zustand";

type ViewportSize = "desktop" | "tablet" | "mobile";

interface PreviewState {
  html: string;
  isLoading: boolean;
  lastUpdated: number;
  viewportSize: ViewportSize;
  error: string | null;

  // Actions
  setHtml: (html: string) => void;
  setLoading: (loading: boolean) => void;
  setViewportSize: (size: ViewportSize) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  html: "",
  isLoading: false,
  lastUpdated: 0,
  viewportSize: "desktop" as ViewportSize,
  error: null,
};

export const usePreviewStore = create<PreviewState>((set) => ({
  ...initialState,

  setHtml: (html) =>
    set({
      html,
      lastUpdated: Date.now(),
      isLoading: false,
      error: null,
    }),

  setLoading: (loading) =>
    set({
      isLoading: loading,
      error: loading ? null : undefined, // Clear error when starting new load
    }),

  setViewportSize: (size) => set({ viewportSize: size }),

  setError: (error) =>
    set({
      error,
      isLoading: false,
    }),

  reset: () => set(initialState),
}));
