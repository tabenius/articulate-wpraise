export interface FeaturedImage {
  id: number;
  url: string;
  altText?: string;
  width?: number;
  height?: number;
}

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
  featuredImage?: FeaturedImage;
}

export interface PostSummary {
  id: number;
  title: string;
  slug: string;
  status: string;
  date: string;
  modified?: string;
  excerpt?: string;
  featuredImage?: FeaturedImage;
}
