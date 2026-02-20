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

  setTemplates: (templates: Template[]) => void;
  setTemplateParts: (parts: TemplatePart[]) => void;
  setCurrentTemplate: (template: Template | null) => void;
  setCurrentTemplatePart: (part: TemplatePart | null) => void;
  updateTemplate: (id: number, updates: Partial<Template>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useTemplateStore = create<TemplateState>((set) => ({
  templates: [],
  templateParts: [],
  currentTemplate: null,
  currentTemplatePart: null,
  isLoading: false,
  error: null,

  setTemplates: (templates) => set({ templates }),

  setTemplateParts: (parts) => set({ templateParts: parts }),

  setCurrentTemplate: (template) => set({ currentTemplate: template }),

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
}));
