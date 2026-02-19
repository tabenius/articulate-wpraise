"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FeaturedImagePanel } from "./featured-image-panel";
import { TaxonomyPanel } from "./taxonomy-panel";
import { PublishPanel } from "./publish-panel";
import { PageSettingsPanel } from "./page-settings-panel";
import { usePostStore } from "@/stores/post-store";

export function PostSettingsDialog() {
  const [open, setOpen] = useState(false);
  const currentPost = usePostStore((s) => s.currentPost);
  const isPage = currentPost?.type === "page";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings2 className="h-4 w-4" />
          {isPage ? "Page" : "Post"} Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{isPage ? "Page" : "Post"} Settings</DialogTitle>
          <DialogDescription>
            Configure {isPage ? "page" : "post"} metadata, featured image, and publishing options
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="publish" className="w-full">
          <TabsList className={`grid w-full ${isPage ? "grid-cols-4" : "grid-cols-3"}`}>
            <TabsTrigger value="publish">Publish</TabsTrigger>
            <TabsTrigger value="image">Featured Image</TabsTrigger>
            <TabsTrigger value="taxonomy">Categories & Tags</TabsTrigger>
            {isPage && <TabsTrigger value="page">Page Options</TabsTrigger>}
          </TabsList>
          <ScrollArea className="h-[500px] mt-4">
            <TabsContent value="publish" className="space-y-4">
              <PublishPanel />
            </TabsContent>
            <TabsContent value="image" className="space-y-4">
              <FeaturedImagePanel />
            </TabsContent>
            <TabsContent value="taxonomy" className="space-y-4">
              <TaxonomyPanel />
            </TabsContent>
            {isPage && (
              <TabsContent value="page" className="space-y-4">
                <PageSettingsPanel />
              </TabsContent>
            )}
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
