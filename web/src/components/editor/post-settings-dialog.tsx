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

export function PostSettingsDialog() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings2 className="h-4 w-4" />
          Post Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Post Settings</DialogTitle>
          <DialogDescription>
            Configure post metadata, featured image, and publishing options
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="publish" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="publish">Publish</TabsTrigger>
            <TabsTrigger value="image">Featured Image</TabsTrigger>
            <TabsTrigger value="taxonomy">Categories & Tags</TabsTrigger>
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
          </ScrollArea>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
