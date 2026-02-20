"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface CreateTemplateDialogProps {
  onTemplateCreated?: (template: { id: number; title: string; slug: string }) => void;
}

const TEMPLATE_TYPES = [
  { value: "index", label: "Index (Home)" },
  { value: "single", label: "Single Post" },
  { value: "page", label: "Page" },
  { value: "archive", label: "Archive" },
  { value: "category", label: "Category" },
  { value: "tag", label: "Tag" },
  { value: "author", label: "Author" },
  { value: "search", label: "Search" },
  { value: "404", label: "404 Error" },
  { value: "custom", label: "Custom Template" },
];

export function CreateTemplateDialog({ onTemplateCreated }: CreateTemplateDialogProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [templateType, setTemplateType] = useState("custom");
  const [isCreating, setIsCreating] = useState(false);
  const { toast } = useToast();

  const handleTitleChange = (value: string) => {
    setTitle(value);
    // Auto-generate slug from title
    const autoSlug = value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
    setSlug(autoSlug);
  };

  const handleCreate = async () => {
    if (!title.trim() || !slug.trim()) {
      toast({
        variant: "destructive",
        title: "Validation error",
        description: "Title and slug are required",
      });
      return;
    }

    try {
      setIsCreating(true);

      const response = await fetch("/api/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          slug: slug.trim(),
          template_type: templateType,
          content: `<!-- wp:heading -->
<h1>${title}</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Start editing your template here.</p>
<!-- /wp:paragraph -->`,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.success === false) {
        // MCP tool returned error (not yet implemented)
        toast({
          variant: "destructive",
          title: "Template creation not available",
          description:
            result.message ||
            "Template creation is not yet fully supported. This feature requires WordPress REST API integration.",
        });
        return;
      }

      toast({
        title: "Template created",
        description: `"${title}" has been created successfully`,
      });

      onTemplateCreated?.(result);
      setOpen(false);
      setTitle("");
      setSlug("");
      setTemplateType("custom");
    } catch (error) {
      console.error("Failed to create template:", error);
      toast({
        variant: "destructive",
        title: "Error creating template",
        description:
          error instanceof Error ? error.message : "Failed to create template",
      });
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="default" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Template</DialogTitle>
          <DialogDescription>
            Create a custom template for your WordPress theme. Templates control
            the layout for different types of pages.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="template-type">Template Type</Label>
            <Select value={templateType} onValueChange={setTemplateType}>
              <SelectTrigger id="template-type">
                <SelectValue placeholder="Select template type" />
              </SelectTrigger>
              <SelectContent>
                {TEMPLATE_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="template-title">Title</Label>
            <Input
              id="template-title"
              placeholder="My Custom Template"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="template-slug">Slug</Label>
            <Input
              id="template-slug"
              placeholder="my-custom-template"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The slug is used in the template filename.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={isCreating}>
            {isCreating ? "Creating..." : "Create Template"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
