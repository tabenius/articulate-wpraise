"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSpeed, setUploadSpeed] = useState(0);
  const [preview, setPreview] = useState<string | null>(currentImage || null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadXhrRef = useRef<XMLHttpRequest | null>(null);
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

    // Upload file with progress tracking
    setUploading(true);
    setUploadProgress(0);
    setUploadSpeed(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("type", type);

    const sessionId = localStorage.getItem("session_id");
    const xhr = new XMLHttpRequest();
    uploadXhrRef.current = xhr;

    let startTime = Date.now();
    let lastLoaded = 0;

    // Track upload progress
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        setUploadProgress(percentComplete);

        // Calculate upload speed (bytes per second)
        const elapsed = (Date.now() - startTime) / 1000;
        const bytesPerSecond = e.loaded / elapsed;
        setUploadSpeed(bytesPerSecond);
      }
    });

    // Handle completion
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          onImageChange(`http://localhost:8000${data.url}`);

          toast({
            title: "Upload successful",
            description: `${label} updated`,
          });
        } catch (error) {
          toast({
            title: "Upload failed",
            description: "Invalid response from server",
            variant: "destructive",
          });
          setPreview(currentImage || null);
        }
      } else {
        toast({
          title: "Upload failed",
          description: `Server error: ${xhr.status}`,
          variant: "destructive",
        });
        setPreview(currentImage || null);
      }
      setUploading(false);
      setUploadProgress(0);
      setUploadSpeed(0);
    });

    // Handle errors
    xhr.addEventListener("error", () => {
      toast({
        title: "Upload failed",
        description: "Network error occurred",
        variant: "destructive",
      });
      setPreview(currentImage || null);
      setUploading(false);
      setUploadProgress(0);
      setUploadSpeed(0);
    });

    // Handle abort
    xhr.addEventListener("abort", () => {
      toast({
        title: "Upload cancelled",
        description: "Upload was cancelled",
      });
      setPreview(currentImage || null);
      setUploading(false);
      setUploadProgress(0);
      setUploadSpeed(0);
    });

    // Send request
    xhr.open("POST", "http://localhost:8000/upload");
    xhr.setRequestHeader("X-Session-ID", sessionId || "");
    xhr.send(formData);
  };

  const handleRemove = () => {
    setPreview(null);
    onImageChange("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleCancelUpload = () => {
    if (uploadXhrRef.current) {
      uploadXhrRef.current.abort();
      uploadXhrRef.current = null;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B/s";
    const k = 1024;
    const sizes = ["B/s", "KB/s", "MB/s"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
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
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">Uploading...</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCancelUpload}
            >
              Cancel
            </Button>
          </div>
          <Progress value={uploadProgress} className="w-full" />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{uploadProgress.toFixed(1)}%</span>
            <span>{formatBytes(uploadSpeed)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
