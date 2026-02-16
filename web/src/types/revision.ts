export interface Revision {
  id: number;
  date: string;
  author: string;
  title: string;
  contentPreview: string;
}

export interface RevisionComparison {
  revision1: {
    id: number;
    date: string;
    author: { name: string };
    title: string;
    content: string;
  };
  revision2: {
    id: number;
    date: string;
    author: { name: string };
    title: string;
    content: string;
  };
}
