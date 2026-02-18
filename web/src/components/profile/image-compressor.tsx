"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Upload, Download, X, Maximize2 } from "lucide-react";

interface ImageCompressorProps {
  onCompressed: (file: File, metadata: CompressionMetadata) => void;
  type: "avatar" | "banner";
}

interface CompressionMetadata {
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
  format: string;
  quality: number;
  dimensions: { width: number; height: number };
}

export function ImageCompressor({ onCompressed, type }: ImageCompressorProps) {
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [compressedUrl, setCompressedUrl] = useState<string | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);

  // Compression settings
  const [format, setFormat] = useState<"webp" | "avif" | "jpeg" | "png">("webp");
  const [quality, setQuality] = useState(85);
  const [maxWidth, setMaxWidth] = useState(type === "avatar" ? 512 : 2048);
  const [maxHeight, setMaxHeight] = useState(type === "avatar" ? 512 : 2048);
  const [enableResize, setEnableResize] = useState(true);

  // Metadata
  const [originalSize, setOriginalSize] = useState(0);
  const [compressedSize, setCompressedSize] = useState(0);
  const [originalDimensions, setOriginalDimensions] = useState({ width: 0, height: 0 });
  const [compressedDimensions, setCompressedDimensions] = useState({ width: 0, height: 0 });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (originalFile) {
      compressImage();
    }
  }, [format, quality, maxWidth, maxHeight, enableResize]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setOriginalFile(file);
    setOriginalSize(file.size);

    // Create object URL for preview
    const url = URL.createObjectURL(file);
    setOriginalUrl(url);

    // Get original dimensions
    const img = new Image();
    img.onload = () => {
      setOriginalDimensions({ width: img.width, height: img.height });
    };
    img.src = url;
  };

  const compressImage = async () => {
    if (!originalFile || !canvasRef.current) return;

    setIsCompressing(true);

    try {
      const img = new Image();
      img.src = originalUrl!;

      await new Promise((resolve) => {
        img.onload = resolve;
      });

      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d")!;

      // Calculate dimensions
      let { width, height } = img;

      if (enableResize) {
        const ratio = Math.min(maxWidth / width, maxHeight / height, 1);
        width = Math.floor(width * ratio);
        height = Math.floor(height * ratio);
      }

      canvas.width = width;
      canvas.height = height;

      // Draw image
      ctx.drawImage(img, 0, 0, width, height);

      // Convert to blob with quality
      const mimeType = `image/${format}`;
      const qualityValue = quality / 100;

      canvas.toBlob(
        (blob) => {
          if (blob) {
            setCompressedSize(blob.size);
            setCompressedDimensions({ width, height });

            const url = URL.createObjectURL(blob);
            setCompressedUrl(url);

            // Create File object
            const compressedFile = new File([blob], `compressed.${format}`, {
              type: mimeType,
            });

            const metadata: CompressionMetadata = {
              originalSize: originalFile.size,
              compressedSize: blob.size,
              compressionRatio:
                ((1 - blob.size / originalFile.size) * 100),
              format,
              quality,
              dimensions: { width, height },
            };

            onCompressed(compressedFile, metadata);
          }
          setIsCompressing(false);
        },
        mimeType,
        qualityValue
      );
    } catch (error) {
      console.error("Compression error:", error);
      setIsCompressing(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const compressionRatio =
    originalSize > 0 ? ((1 - compressedSize / originalSize) * 100).toFixed(1) : "0";

  return (
    <div className="space-y-4">
      <canvas ref={canvasRef} className="hidden" />

      {!originalFile ? (
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-gray-400 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-sm text-gray-600">Click to select an image</p>
          <p className="mt-1 text-xs text-gray-500">
            JPG, PNG, WebP, or AVIF up to 10MB
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Preview Comparison */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs text-gray-500 mb-2 block">Original</Label>
              <Card>
                <CardContent className="p-2">
                  <img
                    src={originalUrl!}
                    alt="Original"
                    className="w-full h-auto rounded"
                  />
                  <div className="mt-2 text-xs space-y-1">
                    <p>Size: {formatBytes(originalSize)}</p>
                    <p>
                      Dimensions: {originalDimensions.width} x {originalDimensions.height}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div>
              <Label className="text-xs text-gray-500 mb-2 block">Compressed</Label>
              <Card>
                <CardContent className="p-2">
                  {compressedUrl ? (
                    <>
                      <img
                        src={compressedUrl}
                        alt="Compressed"
                        className="w-full h-auto rounded"
                      />
                      <div className="mt-2 text-xs space-y-1">
                        <p className="text-green-600 font-medium">
                          Size: {formatBytes(compressedSize)} ({compressionRatio}% smaller)
                        </p>
                        <p>
                          Dimensions: {compressedDimensions.width} x{" "}
                          {compressedDimensions.height}
                        </p>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-32 text-gray-400">
                      {isCompressing ? "Compressing..." : "No preview"}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Settings */}
          <Card>
            <CardContent className="p-4 space-y-4">
              <div className="space-y-2">
                <Label>Format</Label>
                <Tabs value={format} onValueChange={(v: any) => setFormat(v)}>
                  <TabsList className="grid grid-cols-4 w-full">
                    <TabsTrigger value="webp">WebP</TabsTrigger>
                    <TabsTrigger value="avif">AVIF</TabsTrigger>
                    <TabsTrigger value="jpeg">JPEG</TabsTrigger>
                    <TabsTrigger value="png">PNG</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>

              {format !== "png" && (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label>Quality</Label>
                    <span className="text-sm text-gray-500">{quality}%</span>
                  </div>
                  <Slider
                    value={[quality]}
                    onValueChange={(v) => setQuality(v[0])}
                    min={1}
                    max={100}
                    step={1}
                  />
                </div>
              )}

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Resize</Label>
                  <input
                    type="checkbox"
                    checked={enableResize}
                    onChange={(e) => setEnableResize(e.target.checked)}
                    className="rounded"
                  />
                </div>

                {enableResize && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs">Max Width</Label>
                      <input
                        type="number"
                        value={maxWidth}
                        onChange={(e) => setMaxWidth(Number(e.target.value))}
                        className="w-full mt-1 rounded-md border border-gray-300 p-2 text-sm"
                        min="1"
                        max="4096"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Max Height</Label>
                      <input
                        type="number"
                        value={maxHeight}
                        onChange={(e) => setMaxHeight(Number(e.target.value))}
                        className="w-full mt-1 rounded-md border border-gray-300 p-2 text-sm"
                        min="1"
                        max="4096"
                      />
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setOriginalFile(null);
                setOriginalUrl(null);
                setCompressedUrl(null);
                if (fileInputRef.current) {
                  fileInputRef.current.value = "";
                }
              }}
            >
              <X className="mr-2 h-4 w-4" />
              Clear
            </Button>
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="mr-2 h-4 w-4" />
              Select Different Image
            </Button>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/jpg,image/png,image/webp,image/avif"
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
}
