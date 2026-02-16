"use client";

import { useState, useEffect } from "react";
import { usePostStore } from "@/stores/post-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { X, Plus, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useToast } from "@/hooks/use-toast";
import { Term } from "@/types/post";

export function TaxonomyPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const updatePost = usePostStore((s) => s.updatePost);

  const [categories, setCategories] = useState<Term[]>([]);
  const [tags, setTags] = useState<Term[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [categoryOpen, setCategoryOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [creatingCategory, setCreatingCategory] = useState(false);

  const [tagInput, setTagInput] = useState("");
  const { toast } = useToast();
  const [creatingTag, setCreatingTag] = useState(false);

  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [selectedTags, setSelectedTags] = useState<number[]>([]);

  // Load taxonomies from API
  useEffect(() => {
    const loadTaxonomies = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/taxonomies");
        if (res.ok) {
          const data = await res.json();
          setCategories(data.categories || []);
          setTags(data.tags || []);
        }
      } catch (error) {
        console.error("Failed to load taxonomies:", error);
      } finally {
        setLoading(false);
      }
    };
    loadTaxonomies();
  }, []);

  // Initialize selected taxonomies from current post
  useEffect(() => {
    if (currentPost) {
      setSelectedCategories(
        currentPost.categories?.map((c) => c.id) || []
      );
      setSelectedTags(currentPost.tags?.map((t) => t.id) || []);
    }
  }, [currentPost]);

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) return;

    setCreatingCategory(true);
    try {
      const res = await fetch("/api/taxonomies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "category",
          name: newCategoryName,
        }),
      });

      if (!res.ok) throw new Error("Failed to create category");

      const newCategory = await res.json();
      setCategories([...categories, newCategory]);
      setSelectedCategories([...selectedCategories, newCategory.id]);
      setNewCategoryName("");
      toast({ variant: "success", title: "Success", description: "Category created" });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to create category" });
    } finally {
      setCreatingCategory(false);
    }
  };

  const handleCreateTag = async () => {
    if (!tagInput.trim()) return;

    setCreatingTag(true);
    try {
      const res = await fetch("/api/taxonomies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "tag",
          name: tagInput,
        }),
      });

      if (!res.ok) throw new Error("Failed to create tag");

      const newTag = await res.json();
      setTags([...tags, newTag]);
      setSelectedTags([...selectedTags, newTag.id]);
      setTagInput("");
      toast({ variant: "success", title: "Success", description: "Tag created" });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to create tag" });
    } finally {
      setCreatingTag(false);
    }
  };

  const handleSaveTaxonomies = async () => {
    if (!currentPost) return;

    setSaving(true);
    try {
      const res = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category_ids: selectedCategories,
          tag_ids: selectedTags,
        }),
      });

      if (!res.ok) throw new Error("Failed to update taxonomies");

      const updatedPost = await res.json();
      updatePost(currentPost.id, updatedPost);
      toast({ variant: "success", title: "Success", description: "Taxonomies updated" });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to update taxonomies" });
    } finally {
      setSaving(false);
    }
  };

  const toggleCategory = (categoryId: number) => {
    setSelectedCategories((prev) =>
      prev.includes(categoryId)
        ? prev.filter((id) => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const removeTag = (tagId: number) => {
    setSelectedTags((prev) => prev.filter((id) => id !== tagId));
  };

  if (!currentPost) return null;

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Categories & Tags</CardTitle>
        <CardDescription className="text-xs">
          Organize your content with categories and tags
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Categories */}
        <div>
          <Label className="text-xs mb-2 block">Categories</Label>
          <Popover open={categoryOpen} onOpenChange={setCategoryOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start h-8 text-xs"
                disabled={loading}
              >
                {selectedCategories.length > 0
                  ? `${selectedCategories.length} selected`
                  : "Select categories"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[300px] p-0" align="start">
              <Command>
                <CommandInput
                  placeholder="Search categories..."
                  className="h-8 text-xs"
                />
                <CommandList>
                  <CommandEmpty>
                    <div className="p-2">
                      <Input
                        placeholder="New category name"
                        value={newCategoryName}
                        onChange={(e) => setNewCategoryName(e.target.value)}
                        className="h-7 text-xs mb-2"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleCreateCategory();
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        className="w-full h-7"
                        onClick={handleCreateCategory}
                        disabled={!newCategoryName.trim() || creatingCategory}
                      >
                        {creatingCategory ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <>
                            <Plus className="h-3 w-3 mr-1" />
                            Create
                          </>
                        )}
                      </Button>
                    </div>
                  </CommandEmpty>
                  <CommandGroup>
                    {categories.map((category) => (
                      <CommandItem
                        key={category.id}
                        onSelect={() => toggleCategory(category.id)}
                        className="text-xs"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCategories.includes(category.id)}
                          onChange={() => toggleCategory(category.id)}
                          className="mr-2"
                        />
                        {category.name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

          {/* Selected categories */}
          {selectedCategories.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {selectedCategories.map((catId) => {
                const cat = categories.find((c) => c.id === catId);
                return cat ? (
                  <Badge key={catId} variant="secondary" className="text-xs">
                    {cat.name}
                  </Badge>
                ) : null;
              })}
            </div>
          )}
        </div>

        {/* Tags */}
        <div>
          <Label className="text-xs mb-2 block">Tags</Label>
          <div className="flex gap-2">
            <Input
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              className="h-8 text-xs"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  // Check if tag exists
                  const existingTag = tags.find(
                    (t) => t.name.toLowerCase() === tagInput.toLowerCase()
                  );
                  if (existingTag) {
                    if (!selectedTags.includes(existingTag.id)) {
                      setSelectedTags([...selectedTags, existingTag.id]);
                    }
                    setTagInput("");
                  } else {
                    handleCreateTag();
                  }
                }
              }}
              list="tag-suggestions"
            />
            <datalist id="tag-suggestions">
              {tags.map((tag) => (
                <option key={tag.id} value={tag.name} />
              ))}
            </datalist>
            <Button
              size="sm"
              variant="outline"
              className="h-8"
              onClick={() => {
                const existingTag = tags.find(
                  (t) => t.name.toLowerCase() === tagInput.toLowerCase()
                );
                if (existingTag) {
                  if (!selectedTags.includes(existingTag.id)) {
                    setSelectedTags([...selectedTags, existingTag.id]);
                  }
                  setTagInput("");
                } else {
                  handleCreateTag();
                }
              }}
              disabled={!tagInput.trim() || creatingTag}
            >
              {creatingTag ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Plus className="h-3 w-3" />
              )}
            </Button>
          </div>

          {/* Selected tags */}
          {selectedTags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {selectedTags.map((tagId) => {
                const tag = tags.find((t) => t.id === tagId);
                return tag ? (
                  <Badge
                    key={tagId}
                    variant="outline"
                    className="text-xs cursor-pointer"
                    onClick={() => removeTag(tagId)}
                  >
                    {tag.name}
                    <X className="h-3 w-3 ml-1" />
                  </Badge>
                ) : null;
              })}
            </div>
          )}
        </div>

        {/* Save button */}
        <Button
          size="sm"
          onClick={handleSaveTaxonomies}
          disabled={saving}
          className="w-full h-8"
        >
          {saving ? (
            <>
              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            "Save Categories & Tags"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
