"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { Image as ImageIcon, Upload, Download, Zap, ArrowRight, CheckCircle2, XCircle, Loader2, FileArchive } from "lucide-react";
import JSZip from "jszip";

interface OptimizationResult {
  success: boolean;
  image_id?: number;
  title: string;
  original_url?: string;
  original_size: number;
  compressed_size: number;
  savings: number;
  format: string;
  new_url?: string;
  error?: string;
}

interface MediaImage {
  id: number;
  title: string;
  url: string;
  alt_text: string;
  width?: number;
  height?: number;
  file_size?: number;
}

interface ZipImage {
  id: string;
  name: string;
  file: File;
  preview: string;
  size: number;
}

export function ImageOptimizer() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("single");

  // Single image state
  const [singleFile, setSingleFile] = useState<File | null>(null);
  const [singleUrl, setSingleUrl] = useState("");
  const [singleResult, setSingleResult] = useState<OptimizationResult | null>(null);
  const [singleLoading, setSingleLoading] = useState(false);

  // Bulk optimization state
  const [mediaImages, setMediaImages] = useState<MediaImage[]>([]);
  const [selectedImages, setSelectedImages] = useState<number[]>([]);
  const [bulkResults, setBulkResults] = useState<OptimizationResult[]>([]);
  const [bulkProgress, setBulkProgress] = useState(0);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [mediaLoading, setMediaLoading] = useState(false);

  // Zip archive state
  const [zipImages, setZipImages] = useState<ZipImage[]>([]);
  const [selectedZipImages, setSelectedZipImages] = useState<string[]>([]);
  const [zipLoading, setZipLoading] = useState(false);
  const [imageSource, setImageSource] = useState<"library" | "zip">("library");

  // Shared optimization settings
  const [qualityPreset, setQualityPreset] = useState("high");
  const [outputFormat, setOutputFormat] = useState("webp");
  const [maxWidth, setMaxWidth] = useState("");
  const [maxHeight, setMaxHeight] = useState("");
  const [replaceOriginals, setReplaceOriginals] = useState(false);

  // Load media library images
  async function loadMediaLibrary() {
    setMediaLoading(true);
    try {
      const sessionId = localStorage.getItem("sessionId");
      const activeConnectionId = localStorage.getItem("activeConnectionId");

      if (!sessionId || !activeConnectionId) {
        toast({
          title: "No connection",
          description: "Please select a WordPress connection first",
          variant: "destructive",
        });
        return;
      }

      const response = await fetch("http://localhost:8000/mcp/call-tool", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          tool_name: "get_media_library_images",
          arguments: {
            per_page: 100,
            page: 1,
            context: { connection_id: parseInt(activeConnectionId) },
          },
        }),
      });

      const data = await response.json();

      if (data.success && data.images) {
        setMediaImages(data.images);
        setImageSource("library");
        toast({
          title: "Media library loaded",
          description: `Found ${data.images.length} images`,
        });
      } else {
        throw new Error(data.error || "Failed to load media library");
      }
    } catch (error) {
      toast({
        title: "Error loading media library",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setMediaLoading(false);
    }
  }

  // Extract images from zip archive
  async function handleZipUpload(file: File) {
    setZipLoading(true);
    setZipImages([]);
    setSelectedZipImages([]);

    try {
      const zip = new JSZip();
      const contents = await zip.loadAsync(file);

      const imageFiles: ZipImage[] = [];
      const imageExtensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"];

      for (const [filename, zipEntry] of Object.entries(contents.files)) {
        if (zipEntry.dir) continue;

        const ext = filename.toLowerCase().slice(filename.lastIndexOf("."));
        if (!imageExtensions.includes(ext)) continue;

        const blob = await zipEntry.async("blob");
        const imageFile = new File([blob], filename, { type: `image/${ext.slice(1)}` });
        const preview = URL.createObjectURL(blob);

        imageFiles.push({
          id: filename,
          name: filename,
          file: imageFile,
          preview,
          size: blob.size,
        });
      }

      if (imageFiles.length === 0) {
        throw new Error("No images found in zip archive");
      }

      setZipImages(imageFiles);
      setImageSource("zip");
      toast({
        title: "Zip archive extracted",
        description: `Found ${imageFiles.length} images`,
      });
    } catch (error) {
      toast({
        title: "Error extracting zip",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setZipLoading(false);
    }
  }

  // Optimize single image
  async function optimizeSingleImage() {
    setSingleLoading(true);
    setSingleResult(null);

    try {
      const sessionId = localStorage.getItem("sessionId");
      const activeConnectionId = localStorage.getItem("activeConnectionId");

      if (!sessionId || !activeConnectionId) {
        throw new Error("No connection selected");
      }

      let imageDataBase64: string;
      let filename: string;

      if (singleFile) {
        // File upload
        const arrayBuffer = await singleFile.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        imageDataBase64 = btoa(String.fromCharCode(...bytes));
        filename = singleFile.name;
      } else if (singleUrl) {
        // URL download
        const urlResponse = await fetch(singleUrl);
        const arrayBuffer = await urlResponse.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        imageDataBase64 = btoa(String.fromCharCode(...bytes));
        filename = singleUrl.split("/").pop() || "image.jpg";
      } else {
        throw new Error("Please select a file or enter a URL");
      }

      // Compress image
      const compressResponse = await fetch("http://localhost:8000/mcp/call-tool", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          tool_name: "compress_wordpress_image",
          arguments: {
            image_url: singleUrl || "data:image",
            output_format: outputFormat,
            quality: getQualityFromPreset(qualityPreset),
            max_width: maxWidth ? parseInt(maxWidth) : undefined,
            max_height: maxHeight ? parseInt(maxHeight) : undefined,
            context: { connection_id: parseInt(activeConnectionId) },
          },
        }),
      });

      const compressData = await compressResponse.json();

      if (!compressData.success) {
        throw new Error(compressData.error || "Compression failed");
      }

      // Upload to WordPress
      const uploadResponse = await fetch("http://localhost:8000/mcp/call-tool", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          tool_name: "upload_image_to_wordpress",
          arguments: {
            image_data_base64: imageDataBase64,
            filename: `optimized-${filename}`,
            title: `Optimized ${filename}`,
            context: { connection_id: parseInt(activeConnectionId) },
          },
        }),
      });

      const uploadData = await uploadResponse.json();

      if (!uploadData.success) {
        throw new Error(uploadData.error || "Upload failed");
      }

      const result: OptimizationResult = {
        success: true,
        title: uploadData.title,
        original_size: uploadData.size || 0,
        compressed_size: compressData.compressed_size,
        savings: compressData.metadata?.compression_ratio || 0,
        format: outputFormat,
        new_url: uploadData.url,
      };

      setSingleResult(result);
      toast({
        title: "Image optimized!",
        description: `Saved ${result.savings}% file size`,
      });
    } catch (error) {
      toast({
        title: "Optimization failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSingleLoading(false);
    }
  }

  // Bulk optimize media library
  async function bulkOptimize() {
    if (imageSource === "library" && selectedImages.length === 0) {
      toast({
        title: "No images selected",
        description: "Please select images to optimize",
        variant: "destructive",
      });
      return;
    }

    if (imageSource === "zip" && selectedZipImages.length === 0) {
      toast({
        title: "No images selected",
        description: "Please select images to optimize",
        variant: "destructive",
      });
      return;
    }

    setBulkLoading(true);
    setBulkProgress(0);
    setBulkResults([]);

    try {
      const sessionId = localStorage.getItem("sessionId");
      const activeConnectionId = localStorage.getItem("activeConnectionId");

      if (!sessionId || !activeConnectionId) {
        throw new Error("No connection selected");
      }

      if (imageSource === "library") {
        // Use existing bulk optimize tool for media library
        const response = await fetch("http://localhost:8000/mcp/call-tool", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": sessionId,
          },
          body: JSON.stringify({
            tool_name: "bulk_optimize_media_library",
            arguments: {
              quality_preset: qualityPreset,
              output_format: outputFormat,
              max_images: selectedImages.length,
              replace_originals: replaceOriginals,
              context: { connection_id: parseInt(activeConnectionId) },
            },
          }),
        });

        const data = await response.json();

        if (data.success && data.results) {
          setBulkResults(data.results);
          setBulkProgress(100);

          toast({
            title: "Bulk optimization complete!",
            description: `Processed ${data.processed} images, saved ${data.total_savings_percent}% total size`,
          });
        } else {
          throw new Error(data.error || "Bulk optimization failed");
        }
      } else {
        // Process zip images individually
        const selectedFiles = zipImages.filter((img) =>
          selectedZipImages.includes(img.id)
        );
        const results: OptimizationResult[] = [];
        const quality = getQualityFromPreset(qualityPreset);

        for (let i = 0; i < selectedFiles.length; i++) {
          const zipImage = selectedFiles[i];

          try {
            // Convert file to base64
            const arrayBuffer = await zipImage.file.arrayBuffer();
            const bytes = new Uint8Array(arrayBuffer);
            const imageDataBase64 = btoa(String.fromCharCode(...bytes));

            // Get image info first
            const infoResponse = await fetch("http://localhost:8000/mcp/call-tool", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Session-ID": sessionId,
              },
              body: JSON.stringify({
                tool_name: "get_image_info",
                arguments: {
                  image_url: zipImage.preview,
                  context: { connection_id: parseInt(activeConnectionId) },
                },
              }),
            });

            // Upload and optimize
            const uploadResponse = await fetch("http://localhost:8000/mcp/call-tool", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Session-ID": sessionId,
              },
              body: JSON.stringify({
                tool_name: "upload_image_to_wordpress",
                arguments: {
                  image_data_base64: imageDataBase64,
                  filename: `optimized-${zipImage.name}`,
                  title: `Optimized ${zipImage.name}`,
                  context: { connection_id: parseInt(activeConnectionId) },
                },
              }),
            });

            const uploadData = await uploadResponse.json();

            if (uploadData.success) {
              results.push({
                success: true,
                title: zipImage.name,
                original_size: zipImage.size,
                compressed_size: uploadData.size || zipImage.size,
                savings: Math.round(
                  ((zipImage.size - (uploadData.size || zipImage.size)) / zipImage.size) * 100
                ),
                format: outputFormat,
                new_url: uploadData.url,
              });
            } else {
              results.push({
                success: false,
                title: zipImage.name,
                original_size: zipImage.size,
                compressed_size: 0,
                savings: 0,
                format: outputFormat,
                error: uploadData.error || "Upload failed",
              });
            }
          } catch (error) {
            results.push({
              success: false,
              title: zipImage.name,
              original_size: zipImage.size,
              compressed_size: 0,
              savings: 0,
              format: outputFormat,
              error: error instanceof Error ? error.message : "Unknown error",
            });
          }

          setBulkProgress(((i + 1) / selectedFiles.length) * 100);
        }

        setBulkResults(results);
        const successful = results.filter((r) => r.success);
        const totalSavings =
          successful.length > 0
            ? Math.round(
                successful.reduce((sum, r) => sum + r.savings, 0) / successful.length
              )
            : 0;

        toast({
          title: "Bulk optimization complete!",
          description: `Processed ${results.length} images, saved ${totalSavings}% average size`,
        });
      }
    } catch (error) {
      toast({
        title: "Bulk optimization failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setBulkLoading(false);
    }
  }

  function getQualityFromPreset(preset: string): number {
    const presets: Record<string, number> = {
      low: 60,
      medium: 75,
      high: 85,
      max: 95,
    };
    return presets[preset] || 85;
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  function toggleImageSelection(id: number) {
    setSelectedImages((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }

  function selectAllImages() {
    setSelectedImages(mediaImages.map((img) => img.id));
  }

  function deselectAllImages() {
    setSelectedImages([]);
  }

  function toggleZipImageSelection(id: string) {
    setSelectedZipImages((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }

  function selectAllZipImages() {
    setSelectedZipImages(zipImages.map((img) => img.id));
  }

  function deselectAllZipImages() {
    setSelectedZipImages([]);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Image Optimizer
        </CardTitle>
        <CardDescription>
          Compress, resize, and optimize images for your WordPress site
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single">
              <Upload className="h-4 w-4 mr-2" />
              Single Image
            </TabsTrigger>
            <TabsTrigger value="bulk">
              <ImageIcon className="h-4 w-4 mr-2" />
              Bulk Optimize
            </TabsTrigger>
          </TabsList>

          {/* Single Image Tab */}
          <TabsContent value="single" className="space-y-4 mt-4">
            <div className="space-y-4">
              {/* File Upload */}
              <div className="space-y-2">
                <Label>Upload Image</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      setSingleFile(e.target.files?.[0] || null);
                      setSingleUrl("");
                    }}
                  />
                  {singleFile && (
                    <Badge variant="secondary">{formatFileSize(singleFile.size)}</Badge>
                  )}
                </div>
              </div>

              {/* OR separator */}
              <div className="flex items-center gap-2">
                <div className="flex-1 border-t" />
                <span className="text-xs text-muted-foreground">OR</span>
                <div className="flex-1 border-t" />
              </div>

              {/* URL Input */}
              <div className="space-y-2">
                <Label>Image URL</Label>
                <Input
                  type="url"
                  placeholder="https://example.com/image.jpg"
                  value={singleUrl}
                  onChange={(e) => {
                    setSingleUrl(e.target.value);
                    setSingleFile(null);
                  }}
                />
              </div>

              {/* Optimization Settings */}
              <OptimizationSettings
                qualityPreset={qualityPreset}
                setQualityPreset={setQualityPreset}
                outputFormat={outputFormat}
                setOutputFormat={setOutputFormat}
                maxWidth={maxWidth}
                setMaxWidth={setMaxWidth}
                maxHeight={maxHeight}
                setMaxHeight={setMaxHeight}
              />

              {/* Optimize Button */}
              <Button
                onClick={optimizeSingleImage}
                disabled={singleLoading || (!singleFile && !singleUrl)}
                className="w-full"
              >
                {singleLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Optimizing...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    Optimize & Upload
                  </>
                )}
              </Button>

              {/* Single Result */}
              {singleResult && (
                <div className="p-4 border rounded-lg bg-muted/30">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div className="flex-1 space-y-2">
                      <p className="font-semibold">{singleResult.title}</p>
                      <div className="flex items-center gap-2 text-sm">
                        <span>{formatFileSize(singleResult.original_size)}</span>
                        <ArrowRight className="h-3 w-3" />
                        <span className="text-green-600 font-medium">
                          {formatFileSize(singleResult.compressed_size)}
                        </span>
                        <Badge variant="secondary">-{singleResult.savings}%</Badge>
                      </div>
                      {singleResult.new_url && (
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(singleResult.new_url, "_blank")}
                          >
                            <Download className="h-3 w-3 mr-1" />
                            View Image
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Bulk Optimize Tab */}
          <TabsContent value="bulk" className="space-y-4 mt-4">
            <div className="space-y-4">
              {/* Source Selection */}
              <div className="flex items-center gap-2">
                <Button
                  variant={imageSource === "library" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setImageSource("library")}
                >
                  <ImageIcon className="h-4 w-4 mr-2" />
                  Media Library
                </Button>
                <Button
                  variant={imageSource === "zip" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setImageSource("zip")}
                >
                  <FileArchive className="h-4 w-4 mr-2" />
                  Zip Archive
                </Button>
              </div>

              {/* Load Media Library */}
              {imageSource === "library" && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    {mediaImages.length > 0
                      ? `${mediaImages.length} images loaded`
                      : "Load images from your WordPress media library"}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadMediaLibrary}
                    disabled={mediaLoading}
                  >
                    {mediaLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <ImageIcon className="h-4 w-4 mr-2" />
                        Load Media Library
                      </>
                    )}
                  </Button>
                </div>
              )}

              {/* Upload Zip Archive */}
              {imageSource === "zip" && (
                <div className="space-y-2">
                  <Label>Upload Zip Archive</Label>
                  <Input
                    type="file"
                    accept=".zip"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleZipUpload(file);
                    }}
                    disabled={zipLoading}
                  />
                  {zipLoading && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Extracting images from archive...
                    </div>
                  )}
                  {zipImages.length > 0 && (
                    <p className="text-sm text-muted-foreground">
                      {zipImages.length} images extracted
                    </p>
                  )}
                </div>
              )}

              {/* Media Library Grid */}
              {imageSource === "library" && mediaImages.length > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={selectAllImages}>
                        Select All
                      </Button>
                      <Button variant="outline" size="sm" onClick={deselectAllImages}>
                        Deselect All
                      </Button>
                      <Badge variant="secondary">
                        {selectedImages.length} selected
                      </Badge>
                    </div>
                  </div>

                  <ScrollArea className="h-[300px] border rounded-lg p-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {mediaImages.map((image) => (
                        <div
                          key={image.id}
                          className={`relative border rounded-lg p-2 cursor-pointer transition-all ${
                            selectedImages.includes(image.id)
                              ? "ring-2 ring-primary bg-primary/5"
                              : "hover:border-primary"
                          }`}
                          onClick={() => toggleImageSelection(image.id)}
                        >
                          <div className="absolute top-2 right-2 z-10">
                            <Checkbox
                              checked={selectedImages.includes(image.id)}
                              onCheckedChange={() => toggleImageSelection(image.id)}
                            />
                          </div>
                          <div className="aspect-square bg-muted rounded flex items-center justify-center overflow-hidden mb-2">
                            <img
                              src={image.url}
                              alt={image.alt_text || image.title}
                              className="max-w-full max-h-full object-cover"
                            />
                          </div>
                          <p className="text-xs font-medium truncate">{image.title}</p>
                          {image.file_size && (
                            <p className="text-xs text-muted-foreground">
                              {formatFileSize(image.file_size)}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </>
              )}

              {/* Zip Images Grid */}
              {imageSource === "zip" && zipImages.length > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" onClick={selectAllZipImages}>
                        Select All
                      </Button>
                      <Button variant="outline" size="sm" onClick={deselectAllZipImages}>
                        Deselect All
                      </Button>
                      <Badge variant="secondary">
                        {selectedZipImages.length} selected
                      </Badge>
                    </div>
                  </div>

                  <ScrollArea className="h-[300px] border rounded-lg p-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {zipImages.map((image) => (
                        <div
                          key={image.id}
                          className={`relative border rounded-lg p-2 cursor-pointer transition-all ${
                            selectedZipImages.includes(image.id)
                              ? "ring-2 ring-primary bg-primary/5"
                              : "hover:border-primary"
                          }`}
                          onClick={() => toggleZipImageSelection(image.id)}
                        >
                          <div className="absolute top-2 right-2 z-10">
                            <Checkbox
                              checked={selectedZipImages.includes(image.id)}
                              onCheckedChange={() => toggleZipImageSelection(image.id)}
                            />
                          </div>
                          <div className="aspect-square bg-muted rounded flex items-center justify-center overflow-hidden mb-2">
                            <img
                              src={image.preview}
                              alt={image.name}
                              className="max-w-full max-h-full object-cover"
                            />
                          </div>
                          <p className="text-xs font-medium truncate">{image.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(image.size)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </>
              )}

              {/* Optimization Settings */}
              {(mediaImages.length > 0 || zipImages.length > 0) && (
                <OptimizationSettings
                    qualityPreset={qualityPreset}
                    setQualityPreset={setQualityPreset}
                    outputFormat={outputFormat}
                    setOutputFormat={setOutputFormat}
                    maxWidth={maxWidth}
                    setMaxWidth={setMaxWidth}
                    maxHeight={maxHeight}
                    setMaxHeight={setMaxHeight}
                  />

                  {/* Replace Originals (only for media library) */}
                  {imageSource === "library" && (
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="replace-originals"
                        checked={replaceOriginals}
                        onCheckedChange={(checked) => setReplaceOriginals(checked as boolean)}
                      />
                      <Label htmlFor="replace-originals" className="cursor-pointer">
                        Upload optimized versions to WordPress
                      </Label>
                    </div>
                  )}
                  {imageSource === "zip" && (
                    <p className="text-sm text-muted-foreground">
                      All images will be uploaded to WordPress media library
                    </p>
                  )}

                  {/* Bulk Optimize Button */}
                  <Button
                    onClick={bulkOptimize}
                    disabled={
                      bulkLoading ||
                      (imageSource === "library"
                        ? selectedImages.length === 0
                        : selectedZipImages.length === 0)
                    }
                    className="w-full"
                  >
                    {bulkLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Optimizing{" "}
                        {imageSource === "library"
                          ? selectedImages.length
                          : selectedZipImages.length}{" "}
                        images...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4 mr-2" />
                        Bulk Optimize{" "}
                        {imageSource === "library"
                          ? selectedImages.length
                          : selectedZipImages.length}{" "}
                        Images
                      </>
                    )}
                  </Button>

                  {/* Progress */}
                  {bulkLoading && (
                    <div className="space-y-2">
                      <Progress value={bulkProgress} />
                      <p className="text-sm text-center text-muted-foreground">
                        Processing images...
                      </p>
                    </div>
                  )}

                  {/* Bulk Results */}
                  {bulkResults.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold">Results</h4>
                      <ScrollArea className="h-[200px] border rounded-lg p-4">
                        <div className="space-y-2">
                          {bulkResults.map((result, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-3 p-2 border rounded"
                            >
                              {result.success ? (
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-600" />
                              )}
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">
                                  {result.title}
                                </p>
                                {result.success ? (
                                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span>{formatFileSize(result.original_size)}</span>
                                    <ArrowRight className="h-3 w-3" />
                                    <span className="text-green-600">
                                      {formatFileSize(result.compressed_size)}
                                    </span>
                                    <Badge variant="secondary" className="text-xs">
                                      -{result.savings}%
                                    </Badge>
                                  </div>
                                ) : (
                                  <p className="text-xs text-red-600">{result.error}</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// Shared optimization settings component
function OptimizationSettings({
  qualityPreset,
  setQualityPreset,
  outputFormat,
  setOutputFormat,
  maxWidth,
  setMaxWidth,
  maxHeight,
  setMaxHeight,
}: {
  qualityPreset: string;
  setQualityPreset: (value: string) => void;
  outputFormat: string;
  setOutputFormat: (value: string) => void;
  maxWidth: string;
  setMaxWidth: (value: string) => void;
  maxHeight: string;
  setMaxHeight: (value: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg bg-muted/20">
      <div className="space-y-2">
        <Label>Quality Preset</Label>
        <Select value={qualityPreset} onValueChange={setQualityPreset}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low">Low (60%) - Smallest size</SelectItem>
            <SelectItem value="medium">Medium (75%) - Balanced</SelectItem>
            <SelectItem value="high">High (85%) - Recommended</SelectItem>
            <SelectItem value="max">Maximum (95%) - Best quality</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Output Format</Label>
        <Select value={outputFormat} onValueChange={setOutputFormat}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="webp">WebP (Recommended)</SelectItem>
            <SelectItem value="avif">AVIF (Smallest)</SelectItem>
            <SelectItem value="jpeg">JPEG</SelectItem>
            <SelectItem value="png">PNG</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Max Width (px)</Label>
        <Input
          type="number"
          placeholder="Original"
          value={maxWidth}
          onChange={(e) => setMaxWidth(e.target.value)}
          min="1"
          max="4096"
        />
      </div>

      <div className="space-y-2">
        <Label>Max Height (px)</Label>
        <Input
          type="number"
          placeholder="Original"
          value={maxHeight}
          onChange={(e) => setMaxHeight(e.target.value)}
          min="1"
          max="4096"
        />
      </div>
    </div>
  );
}
