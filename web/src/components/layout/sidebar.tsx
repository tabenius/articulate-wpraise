"use client";

import { useState, useMemo } from "react";
import { usePostStore } from "@/stores/post-store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { FileText, File, Plus, X, Search, RefreshCw } from "lucide-react";
import type { PostSummary } from "@/types/post";
import { PostListSkeleton } from "./post-list-skeleton";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPost: (postId: number, type?: string) => void;
  onCreatePost: () => void;
  onRefresh?: () => void;
}

export function Sidebar({ isOpen, onClose, onSelectPost, onCreatePost, onRefresh }: SidebarProps) {
  const posts = usePostStore((s) => s.posts);
  const currentPost = usePostStore((s) => s.currentPost);
  const isLoading = usePostStore((s) => s.isLoading);
  const [searchQuery, setSearchQuery] = useState("");

  // Filter and group by type
  const { filteredPosts, filteredPages } = useMemo(() => {
    const query = searchQuery.toLowerCase();
    const filtered = searchQuery.trim()
      ? posts.filter((p) =>
          p.title.toLowerCase().includes(query) ||
          p.status.toLowerCase().includes(query)
        )
      : posts;
    return {
      filteredPosts: filtered.filter((p) => p.type !== "page"),
      filteredPages: filtered.filter((p) => p.type === "page"),
    };
  }, [posts, searchQuery]);

  if (!isOpen) return null;

  return (
    <div className="absolute inset-0 z-50 flex">
      <div className="w-80 bg-background border-r shadow-lg flex flex-col">
        <div className="p-4 border-b space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Posts</h2>
            <div className="flex gap-1">
              {onRefresh && (
                <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh">
                  <RefreshCw className="h-4 w-4" />
                </Button>
              )}
              <Button variant="ghost" size="icon" onClick={onCreatePost} title="New Post">
                <Plus className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search posts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        <ScrollArea className="flex-1">
          {isLoading ? (
            <PostListSkeleton />
          ) : filteredPosts.length === 0 && filteredPages.length === 0 && searchQuery ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No results for &quot;{searchQuery}&quot;
            </div>
          ) : posts.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mb-3" />
              <h3 className="font-medium text-sm mb-1">No posts yet</h3>
              <p className="text-xs text-muted-foreground mb-4">
                Get started by creating your first post
              </p>
              <Button size="sm" onClick={onCreatePost}>
                <Plus className="h-4 w-4 mr-1" />
                Create Post
              </Button>
            </div>
          ) : (
            <div className="p-2">
              {filteredPosts.length > 0 && (
                <>
                  <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Posts
                  </div>
                  {filteredPosts.map((post) => (
                    <PostItem
                      key={`post-${post.id}`}
                      post={post}
                      icon={<FileText className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />}
                      isActive={currentPost?.id === post.id && currentPost?.type !== "page"}
                      onClick={() => onSelectPost(post.id, "post")}
                    />
                  ))}
                </>
              )}
              {filteredPages.length > 0 && (
                <>
                  <div className="px-3 py-1.5 mt-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Pages
                  </div>
                  {filteredPages.map((page) => (
                    <PostItem
                      key={`page-${page.id}`}
                      post={page}
                      icon={<File className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />}
                      isActive={currentPost?.id === page.id && currentPost?.type === "page"}
                      onClick={() => onSelectPost(page.id, "page")}
                    />
                  ))}
                </>
              )}
            </div>
          )}
        </ScrollArea>
      </div>

      <div className="flex-1 bg-black/20" onClick={onClose} />
    </div>
  );
}

function PostItem({
  post,
  icon,
  isActive,
  onClick,
}: {
  post: PostSummary;
  icon: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
        isActive
          ? "bg-primary/10 border border-primary/20"
          : "hover:bg-accent"
      }`}
    >
      <div className="flex items-start gap-2">
        {icon}
        <div className="min-w-0">
          <div className="font-medium text-sm truncate">
            {post.title || "Untitled"}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-xs">
              {post.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {new Date(post.date).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}
