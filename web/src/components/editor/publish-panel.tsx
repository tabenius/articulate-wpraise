"use client";

import { useState } from "react";
import { usePostStore } from "@/stores/post-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calendar, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export function PublishPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const updatePost = usePostStore((s) => s.updatePost);
  const { toast } = useToast();

  const [scheduledDate, setScheduledDate] = useState("");
  const [scheduledTime, setScheduledTime] = useState("");
  const [scheduling, setScheduling] = useState(false);

  const handleSchedule = async () => {
    if (!currentPost || !scheduledDate || !scheduledTime) return;

    // Combine date and time to ISO 8601 format
    const dateTimeString = `${scheduledDate}T${scheduledTime}:00`;
    const dateTime = new Date(dateTimeString);

    if (isNaN(dateTime.getTime())) {
      toast({ variant: "destructive", title: "Error", description: "Invalid date or time" });
      return;
    }

    // Check if date is in the future
    if (dateTime <= new Date()) {
      toast({ variant: "destructive", title: "Error", description: "Scheduled date must be in the future" });
      return;
    }

    setScheduling(true);
    try {
      const res = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: dateTime.toISOString(),
          status: "publish", // WordPress will set to 'future' automatically
        }),
      });

      if (!res.ok) throw new Error("Failed to schedule post");

      const updatedPost = await res.json();
      updatePost(currentPost.id, updatedPost);

      toast({ variant: "success", title: "Success", description: `Post scheduled for ${dateTime.toLocaleString()}` });
      setScheduledDate("");
      setScheduledTime("");
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to schedule post" });
    } finally {
      setScheduling(false);
    }
  };

  const handlePublishNow = async () => {
    if (!currentPost) return;

    setScheduling(true);
    try {
      const res = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "publish",
          date: new Date().toISOString(),
        }),
      });

      if (!res.ok) throw new Error("Failed to publish post");

      const updatedPost = await res.json();
      updatePost(currentPost.id, updatedPost);

      toast({ variant: "success", title: "Success", description: "Post published successfully" });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to publish post" });
    } finally {
      setScheduling(false);
    }
  };

  if (!currentPost) return null;

  const isScheduled = currentPost.status === "future";
  const isPublished = currentPost.status === "publish";

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Publish</CardTitle>
        <CardDescription className="text-xs">
          {isScheduled
            ? `Scheduled for ${new Date(currentPost.date).toLocaleString()}`
            : isPublished
            ? `Published on ${new Date(currentPost.date).toLocaleString()}`
            : "Schedule or publish your post"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {!isScheduled && !isPublished && (
          <>
            {/* Quick Publish */}
            <Button
              size="sm"
              onClick={handlePublishNow}
              disabled={scheduling}
              className="w-full h-8"
              variant="default"
            >
              {scheduling ? (
                <>
                  <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                  Publishing...
                </>
              ) : (
                "Publish Now"
              )}
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Or schedule for later
                </span>
              </div>
            </div>

            {/* Schedule for Later */}
            <div className="space-y-2">
              <div>
                <Label htmlFor="schedule-date" className="text-xs">
                  Date
                </Label>
                <Input
                  id="schedule-date"
                  type="date"
                  value={scheduledDate}
                  onChange={(e) => setScheduledDate(e.target.value)}
                  className="h-8 text-xs"
                  min={new Date().toISOString().split("T")[0]}
                />
              </div>
              <div>
                <Label htmlFor="schedule-time" className="text-xs">
                  Time
                </Label>
                <Input
                  id="schedule-time"
                  type="time"
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleSchedule}
                disabled={
                  !scheduledDate || !scheduledTime || scheduling
                }
                className="w-full h-8"
              >
                {scheduling ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                    Scheduling...
                  </>
                ) : (
                  <>
                    <Calendar className="h-3 w-3 mr-2" />
                    Schedule Post
                  </>
                )}
              </Button>
            </div>
          </>
        )}

        {(isScheduled || isPublished) && (
          <div className="text-xs text-muted-foreground">
            {isScheduled && (
              <p>
                This post is scheduled to be published automatically at the set
                time.
              </p>
            )}
            {isPublished && <p>This post is live and publicly visible.</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
