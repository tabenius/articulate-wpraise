"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FontUploadProps {
  onUploadSuccess?: () => void;
}

export function FontUpload({ onUploadSuccess }: FontUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSpeed, setUploadSpeed] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fontFamily, setFontFamily] = useState("");
  const [fontWeight, setFontWeight] = useState("400");
  const [fontStyle, setFontStyle] = useState("normal");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadXhrRef = useRef<XMLHttpRequest | null>(null);
  const { toast } = useToast();

  const extractFontFamily = (filename: string): string => {
    // Remove file extension
    let name = filename.replace(/\.(woff2|woff|ttf|otf|eot)$/i, "");
    // Remove common suffixes
    name = name.replace(/-?(regular|bold|italic|light|medium|semibold|thin|black|oblique)$/i, "");
    // Remove weight indicators
    name = name.replace(/-?(100|200|300|400|500|600|700|800|900)$/i, "");
    // Convert to title case
    return name
      .split(/[-_]/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ");
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validExtensions = [".woff2", ".woff", ".ttf", ".otf", ".eot"];
    const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
    if (!validExtensions.includes(fileExt)) {
      toast({
        title: "Invalid file type",
        description: "Please upload WOFF2, WOFF, TTF, OTF, or EOT font file",
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

    setSelectedFile(file);

    // Auto-extract font family from filename if not already set
    if (!fontFamily) {
      const extractedName = extractFontFamily(file.name);
      setFontFamily(extractedName);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadSpeed(0);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("font_family", fontFamily);
    formData.append("font_weight", fontWeight);
    formData.append("font_style", fontStyle);

    const xhr = new XMLHttpRequest();
    uploadXhrRef.current = xhr;

    let startTime = Date.now();

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

          if (data.error) {
            toast({
              title: "Upload failed",
              description: data.error,
              variant: "destructive",
            });
          } else {
            toast({
              title: "Font uploaded successfully",
              description: `${fontFamily} is now available for use`,
            });

            // Reset form
            setSelectedFile(null);
            setFontFamily("");
            setFontWeight("400");
            setFontStyle("normal");
            if (fileInputRef.current) {
              fileInputRef.current.value = "";
            }

            // Notify parent
            onUploadSuccess?.();
          }
        } catch (error) {
          toast({
            title: "Upload failed",
            description: "Invalid response from server",
            variant: "destructive",
          });
        }
      } else {
        toast({
          title: "Upload failed",
          description: `Server error: ${xhr.status}`,
          variant: "destructive",
        });
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
      setUploading(false);
      setUploadProgress(0);
      setUploadSpeed(0);
    });

    // Send request
    xhr.open("POST", "/api/fonts/upload");
    xhr.send(formData);
  };

  const handleCancelUpload = () => {
    if (uploadXhrRef.current) {
      uploadXhrRef.current.abort();
      uploadXhrRef.current = null;
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
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
    <div className="space-y-4 p-6 border rounded-lg bg-card">
      <h3 className="text-lg font-semibold">Upload Font</h3>

      {/* File selection */}
      {!selectedFile ? (
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 flex items-center justify-center cursor-pointer hover:border-gray-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="text-center">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm font-medium text-gray-700">Click to upload font</p>
            <p className="text-xs text-gray-500 mt-1">WOFF2, WOFF, TTF, OTF, EOT</p>
            <p className="text-xs text-gray-500">Max 5MB</p>
          </div>
        </div>
      ) : (
        <div className="border rounded-lg p-4 bg-muted">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">
                {(selectedFile.size / 1024).toFixed(2)} KB
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRemoveFile}
              disabled={uploading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".woff2,.woff,.ttf,.otf,.eot"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Font metadata inputs */}
      {selectedFile && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="font-family">Font Family Name</Label>
            <Input
              id="font-family"
              value={fontFamily}
              onChange={(e) => setFontFamily(e.target.value)}
              placeholder="e.g., Roboto"
              disabled={uploading}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="font-weight">Font Weight</Label>
              <Select value={fontWeight} onValueChange={setFontWeight} disabled={uploading}>
                <SelectTrigger id="font-weight">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="100">100 (Thin)</SelectItem>
                  <SelectItem value="200">200 (Extra Light)</SelectItem>
                  <SelectItem value="300">300 (Light)</SelectItem>
                  <SelectItem value="400">400 (Regular)</SelectItem>
                  <SelectItem value="500">500 (Medium)</SelectItem>
                  <SelectItem value="600">600 (Semi Bold)</SelectItem>
                  <SelectItem value="700">700 (Bold)</SelectItem>
                  <SelectItem value="800">800 (Extra Bold)</SelectItem>
                  <SelectItem value="900">900 (Black)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="font-style">Font Style</Label>
              <Select value={fontStyle} onValueChange={setFontStyle} disabled={uploading}>
                <SelectTrigger id="font-style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="italic">Italic</SelectItem>
                  <SelectItem value="oblique">Oblique</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Preview text */}
          {fontFamily && (
            <div className="space-y-2">
              <Label>Preview</Label>
              <div
                className="border rounded-lg p-4 bg-background"
                style={{
                  fontFamily: `'${fontFamily}', sans-serif`,
                  fontWeight: parseInt(fontWeight),
                  fontStyle: fontStyle,
                }}
              >
                <p className="text-2xl">The quick brown fox jumps over the lazy dog</p>
                <p className="text-sm text-gray-500 mt-2">
                  {fontFamily} · {fontWeight} · {fontStyle}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload button and progress */}
      {selectedFile && !uploading && (
        <Button onClick={handleUpload} className="w-full" disabled={!fontFamily}>
          Upload Font
        </Button>
      )}

      {uploading && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">Uploading...</span>
            <Button type="button" variant="outline" size="sm" onClick={handleCancelUpload}>
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
