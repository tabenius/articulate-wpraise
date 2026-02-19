"use client";

import { useState, useRef } from "react";
import { usePostStore } from "@/stores/post-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { X, Upload, Loader2, Link as LinkIcon } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export function FeaturedImagePanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const updatePost = usePostStore((s) => s.updatePost);
  const [imageUrl, setImageUrl] = useState("");
  const [altText, setAltText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviewUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile || !currentPost) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("alt_text", altText);

      const uploadRes = await fetch("/api/media", {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        throw new Error("Failed to upload file");
      }

      const uploadData = await uploadRes.json();

      if (uploadData.error) {
        throw new Error(uploadData.error);
      }

      // Update the post with the featured image
      const updateRes = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          featured_image_id: uploadData.id,
        }),
      });

      if (!updateRes.ok) {
        throw new Error("Failed to set featured image");
      }

      const updatedPost = await updateRes.json();
      updatePost(currentPost.id, updatedPost);

      toast({ title: "Success", description: "Featured image uploaded successfully" });
      setSelectedFile(null);
      setPreviewUrl("");
      setAltText("");
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to upload file" });
    } finally {
      setUploading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!imageUrl || !currentPost) return;

    setUploading(true);
    try {
      const uploadRes = await fetch("/api/media", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_url: imageUrl,
          alt_text: altText,
        }),
      });

      if (!uploadRes.ok) {
        throw new Error("Failed to upload image");
      }

      const uploadData = await uploadRes.json();

      if (uploadData.error) {
        throw new Error(uploadData.error);
      }

      // Update the post with the featured image
      const updateRes = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          featured_image_id: uploadData.id,
        }),
      });

      if (!updateRes.ok) {
        throw new Error("Failed to set featured image");
      }

      const updatedPost = await updateRes.json();
      updatePost(currentPost.id, updatedPost);

      toast({ title: "Success", description: "Featured image uploaded successfully" });
      setImageUrl("");
      setAltText("");
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to upload image" });
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = async () => {
    if (!currentPost) return;

    try {
      const res = await fetch(`/api/posts/${currentPost.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          featured_image_id: 0, // 0 removes the featured image
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to remove featured image");
      }

      const updatedPost = await res.json();
      updatePost(currentPost.id, updatedPost);

      toast({ variant: "success", title: "Success", description: "Featured image removed" });
    } catch (error) {
      toast({ variant: "destructive", title: "Error", description: error instanceof Error ? error.message : "Failed to remove image" });
    }
  };

  if (!currentPost) return null;

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Featured Image</CardTitle>
        <CardDescription className="text-xs">
          Add a featured image for this post
        </CardDescription>
      </CardHeader>
      <CardContent>
        {currentPost.featuredImage ? (
          <div className="space-y-3">
            <div className="relative group">
              <img
                src={currentPost.featuredImage.url}
                alt={currentPost.featuredImage.altText || "Featured image"}
                className="w-full h-48 object-cover rounded-md border"
              />
              <Button
                size="sm"
                variant="destructive"
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={handleRemove}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            {currentPost.featuredImage.altText && (
              <p className="text-xs text-muted-foreground">
                {currentPost.featuredImage.altText}
              </p>
            )}
          </div>
        ) : (
          <Tabs defaultValue="file" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="file">Upload File</TabsTrigger>
              <TabsTrigger value="url">From URL</TabsTrigger>
            </TabsList>

            <TabsContent value="file" className="space-y-3 mt-3">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />

              {previewUrl ? (
                <div className="space-y-3">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-48 object-cover rounded-md border"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedFile(null);
                      setPreviewUrl("");
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="w-full h-8"
                  >
                    <X className="h-3 w-3 mr-2" />
                    Clear
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full h-16 border-dashed"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Choose Image File
                </Button>
              )}

              <div>
                <Label htmlFor="alt-text-file" className="text-xs">
                  Alt Text (optional)
                </Label>
                <Input
                  id="alt-text-file"
                  placeholder="Image description"
                  value={altText}
                  onChange={(e) => setAltText(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <Button
                size="sm"
                onClick={handleFileUpload}
                disabled={!selectedFile || uploading}
                className="w-full h-8"
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="h-3 w-3 mr-2" />
                    Upload & Set Featured Image
                  </>
                )}
              </Button>
            </TabsContent>

            <TabsContent value="url" className="space-y-3 mt-3">
              <div>
                <Label htmlFor="image-url" className="text-xs">
                  Image URL
                </Label>
                <Input
                  id="image-url"
                  placeholder="https://example.com/image.jpg"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
              <div>
                <Label htmlFor="alt-text-url" className="text-xs">
                  Alt Text (optional)
                </Label>
                <Input
                  id="alt-text-url"
                  placeholder="Image description"
                  value={altText}
                  onChange={(e) => setAltText(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
              <Button
                size="sm"
                onClick={handleUrlUpload}
                disabled={!imageUrl || uploading}
                className="w-full h-8"
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <LinkIcon className="h-3 w-3 mr-2" />
                    Upload & Set Featured Image
                  </>
                )}
              </Button>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}
