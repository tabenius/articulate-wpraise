"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Upload, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ImageUploadProps {
  currentImage?: string | null;
  onImageChange: (url: string) => void;
  type: "avatar" | "banner";
  label: string;
}

export function ImageUpload({ currentImage, onImageChange, type, label }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(currentImage || null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/avif"];
    if (!validTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload JPG, PNG, WebP, or AVIF image",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Maximum file size is 5MB",
        variant: "destructive",
      });
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Upload file
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("type", type);

      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        headers: {
          "X-Session-ID": sessionId || "",
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();
      onImageChange(`http://localhost:8000${data.url}`);

      toast({
        title: "Upload successful",
        description: `${label} updated`,
      });
    } catch (error) {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
      setPreview(currentImage || null);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = () => {
    setPreview(null);
    onImageChange("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">{label}</label>

      {preview ? (
        <div className="relative">
          <img
            src={preview}
            alt={label}
            className={
              type === "avatar"
                ? "w-32 h-32 rounded-full object-cover border-2 border-gray-200"
                : "w-full h-48 rounded-lg object-cover border-2 border-gray-200"
            }
          />
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleRemove}
            className="absolute top-2 right-2"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <div
          className={`border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center cursor-pointer hover:border-gray-400 transition-colors ${
            type === "avatar" ? "w-32 h-32" : "w-full h-48"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="text-center">
            <Upload className="mx-auto h-8 w-8 text-gray-400" />
            <p className="mt-2 text-sm text-gray-500">Click to upload</p>
            <p className="text-xs text-gray-400">JPG, PNG, WebP, AVIF</p>
            <p className="text-xs text-gray-400">Max 5MB</p>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.avif"
        onChange={handleFileSelect}
        className="hidden"
      />

      {uploading && (
        <p className="text-sm text-gray-500">Uploading...</p>
      )}
    </div>
  );
}
