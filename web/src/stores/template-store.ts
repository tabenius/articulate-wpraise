import { create } from "zustand";

interface Template {
  id: number;
  title: string;
  slug: string;
  content: string;
}

interface TemplatePart {
  id: number;
  title: string;
  slug: string;
  content: string;
}

interface TemplateState {
  templates: Template[];
  templateParts: TemplatePart[];
  currentTemplate: Template | null;
  currentTemplatePart: TemplatePart | null;
  isLoading: boolean;
  error: string | null;
  favorites: number[];
  recentTemplates: number[];

  setTemplates: (templates: Template[]) => void;
  setTemplateParts: (parts: TemplatePart[]) => void;
  setCurrentTemplate: (template: Template | null) => void;
  setCurrentTemplatePart: (part: TemplatePart | null) => void;
  updateTemplate: (id: number, updates: Partial<Template>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  toggleFavorite: (id: number) => void;
  addToRecent: (id: number) => void;
}

// Load favorites and recents from localStorage
const loadFavorites = (): number[] => {
  if (typeof window === "undefined") return [];
  const saved = localStorage.getItem("template-favorites");
  return saved ? JSON.parse(saved) : [];
};

const loadRecents = (): number[] => {
  if (typeof window === "undefined") return [];
  const saved = localStorage.getItem("template-recents");
  return saved ? JSON.parse(saved) : [];
};

export const useTemplateStore = create<TemplateState>((set) => ({
  templates: [],
  templateParts: [],
  currentTemplate: null,
  currentTemplatePart: null,
  isLoading: false,
  error: null,
  favorites: loadFavorites(),
  recentTemplates: loadRecents(),

  setTemplates: (templates) => set({ templates }),

  setTemplateParts: (parts) => set({ templateParts: parts }),

  setCurrentTemplate: (template) => {
    set({ currentTemplate: template });
    // Add to recent when template is selected
    if (template) {
      set((state) => {
        const newRecents = [
          template.id,
          ...state.recentTemplates.filter((id) => id !== template.id),
        ].slice(0, 10); // Keep only 10 most recent
        localStorage.setItem("template-recents", JSON.stringify(newRecents));
        return { recentTemplates: newRecents };
      });
    }
  },

  setCurrentTemplatePart: (part) => set({ currentTemplatePart: part }),

  updateTemplate: (id, updates) =>
    set((state) => ({
      templates: state.templates.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
      currentTemplate:
        state.currentTemplate?.id === id
          ? { ...state.currentTemplate, ...updates }
          : state.currentTemplate,
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  toggleFavorite: (id) =>
    set((state) => {
      const newFavorites = state.favorites.includes(id)
        ? state.favorites.filter((fid) => fid !== id)
        : [...state.favorites, id];
      localStorage.setItem("template-favorites", JSON.stringify(newFavorites));
      return { favorites: newFavorites };
    }),

  addToRecent: (id) =>
    set((state) => {
      const newRecents = [
        id,
        ...state.recentTemplates.filter((rid) => rid !== id),
      ].slice(0, 10);
      localStorage.setItem("template-recents", JSON.stringify(newRecents));
      return { recentTemplates: newRecents };
    }),
}));
