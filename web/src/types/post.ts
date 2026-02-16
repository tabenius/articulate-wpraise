export interface FeaturedImage {
  id: number;
  url: string;
  altText?: string;
  width?: number;
  height?: number;
}

export interface Term {
  id: number;
  name: string;
  slug: string;
  description?: string;
  count?: number;
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
  categories?: Term[];
  tags?: Term[];
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
  categories?: Term[];
  tags?: Term[];
}
