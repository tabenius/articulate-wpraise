export interface Post {
  id: number;
  title: string;
  slug: string;
  status: string;
  content?: string;
  date: string;
  modified?: string;
  excerpt?: string;
  author?: string;
}

export interface PostSummary {
  id: number;
  title: string;
  slug: string;
  status: string;
  date: string;
  modified?: string;
  excerpt?: string;
}
