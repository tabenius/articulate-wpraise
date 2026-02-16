"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Clock, RotateCcw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { usePostStore } from "@/stores/post-store";
import { Revision } from "@/types/revision";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return "just now";
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} hour${hours !== 1 ? "s" : ""} ago`;
  } else if (diffInSeconds < 2592000) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days !== 1 ? "s" : ""} ago`;
  } else if (diffInSeconds < 31536000) {
    const months = Math.floor(diffInSeconds / 2592000);
    return `${months} month${months !== 1 ? "s" : ""} ago`;
  } else {
    const years = Math.floor(diffInSeconds / 31536000);
    return `${years} year${years !== 1 ? "s" : ""} ago`;
  }
}

export function RevisionTimeline() {
  const [open, setOpen] = useState(false);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRevision, setSelectedRevision] = useState<number | null>(null);
  const currentPost = usePostStore((s) => s.currentPost);
  const { toast } = useToast();

  useEffect(() => {
    if (open && currentPost) {
      fetchRevisions();
    }
  }, [open, currentPost]);

  const fetchRevisions = async () => {
    if (!currentPost) return;

    setLoading(true);
    try {
      const response = await fetch(
        `/api/revisions?postId=${currentPost.id}&limit=50`
      );
      const data = await response.json();
      setRevisions(data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load revisions",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (revisionId: number) => {
    if (!currentPost) return;

    try {
      const response = await fetch("/api/revisions/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          postId: currentPost.id,
          revisionId,
        }),
      });

      if (response.ok) {
        toast({
          variant: "success",
          title: "Revision restored",
          description: "Post has been restored to the selected revision",
        });
        setOpen(false);
        // Trigger post reload
        window.location.reload();
      } else {
        throw new Error("Failed to restore");
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to restore revision",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Clock className="h-4 w-4 mr-2" />
          Revisions
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Revision History
          </DialogTitle>
          <DialogDescription>
            View and restore previous versions of this post
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[calc(80vh-8rem)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : revisions.length === 0 ? (
            <div className="text-center text-muted-foreground py-12">
              <Clock className="h-12 w-12 mx-auto mb-4 opacity-40" />
              <p>No revisions found</p>
            </div>
          ) : (
            <div className="space-y-2 pr-4">
              {revisions.map((revision, index) => (
                <div
                  key={revision.id}
                  className={`border rounded-lg p-4 hover:bg-accent/50 transition-colors cursor-pointer ${
                    selectedRevision === revision.id ? "bg-accent" : ""
                  }`}
                  onClick={() => setSelectedRevision(revision.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm">
                          {revision.author}
                        </span>
                        {index === 0 && (
                          <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatRelativeTime(revision.date)}
                      </div>
                    </div>
                    {index !== 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRestore(revision.id);
                        }}
                      >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Restore
                      </Button>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground line-clamp-2">
                    {revision.contentPreview}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
