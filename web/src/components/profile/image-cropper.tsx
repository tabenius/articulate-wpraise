"use client";

import { useState, useRef, useEffect } from "react";
import ReactCrop, { Crop, PixelCrop, centerCrop, makeAspectCrop } from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Crop as CropIcon, RotateCw, ZoomIn, ZoomOut } from "lucide-react";

interface ImageCropperProps {
  imageSrc: string;
  aspectRatio?: number;
  onCropComplete: (croppedBlob: Blob, croppedUrl: string) => void;
  type: "avatar" | "banner";
}

const ASPECT_RATIOS = {
  avatar: 1, // 1:1
  banner: 16 / 9, // 16:9
  free: 0, // Free form
};

export function ImageCropper({ imageSrc, aspectRatio, onCropComplete, type }: ImageCropperProps) {
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [scale, setScale] = useState(1);
  const [rotate, setRotate] = useState(0);
  const [aspect, setAspect] = useState<number | undefined>(
    aspectRatio || ASPECT_RATIOS[type]
  );

  const imgRef = useRef<HTMLImageElement>(null);
  const previewCanvasRef = useRef<HTMLCanvasElement>(null);

  // Initialize crop when image loads
  function onImageLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const { width, height } = e.currentTarget;

    const crop = centerCrop(
      makeAspectCrop(
        {
          unit: "%",
          width: 90,
        },
        aspect || 1,
        width,
        height
      ),
      width,
      height
    );

    setCrop(crop);
  }

  // Generate cropped image preview
  useEffect(() => {
    if (!completedCrop || !imgRef.current || !previewCanvasRef.current) {
      return;
    }

    const image = imgRef.current;
    const canvas = previewCanvasRef.current;
    const crop = completedCrop;

    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = crop.width;
    canvas.height = crop.height;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingQuality = "high";

    ctx.drawImage(
      image,
      crop.x * scaleX,
      crop.y * scaleY,
      crop.width * scaleX,
      crop.height * scaleY,
      0,
      0,
      crop.width,
      crop.height
    );
  }, [completedCrop]);

  const handleCropClick = async () => {
    if (!previewCanvasRef.current || !completedCrop) {
      return;
    }

    const canvas = previewCanvasRef.current;

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          console.error("Failed to create blob");
          return;
        }

        const croppedUrl = URL.createObjectURL(blob);
        onCropComplete(blob, croppedUrl);
      },
      "image/png",
      1
    );
  };

  const handleRotate = () => {
    setRotate((prev) => (prev + 90) % 360);
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.1, 3));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.1, 0.5));
  };

  const handleAspectChange = (value: string) => {
    const aspectValue = value === "free" ? undefined : parseFloat(value);
    setAspect(aspectValue);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-4">
          {/* Aspect Ratio Selector */}
          <div className="mb-4">
            <label className="text-sm font-medium mb-2 block">Aspect Ratio</label>
            <Tabs
              value={aspect?.toString() || "free"}
              onValueChange={handleAspectChange}
            >
              <TabsList className="grid grid-cols-4 w-full">
                <TabsTrigger value="1">1:1</TabsTrigger>
                <TabsTrigger value={String(4 / 3)}>4:3</TabsTrigger>
                <TabsTrigger value={String(16 / 9)}>16:9</TabsTrigger>
                <TabsTrigger value="free">Free</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Crop Controls */}
          <div className="flex gap-2 mb-4">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRotate}
            >
              <RotateCw className="h-4 w-4 mr-2" />
              Rotate
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
            >
              <ZoomIn className="h-4 w-4 mr-2" />
              Zoom In
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
            >
              <ZoomOut className="h-4 w-4 mr-2" />
              Zoom Out
            </Button>
          </div>

          {/* Crop Area */}
          <div className="flex justify-center mb-4">
            <ReactCrop
              crop={crop}
              onChange={(c) => setCrop(c)}
              onComplete={(c) => setCompletedCrop(c)}
              aspect={aspect}
            >
              <img
                ref={imgRef}
                src={imageSrc}
                alt="Crop preview"
                style={{
                  transform: `scale(${scale}) rotate(${rotate}deg)`,
                  maxWidth: "100%",
                  maxHeight: "500px",
                }}
                onLoad={onImageLoad}
              />
            </ReactCrop>
          </div>

          {/* Preview Canvas (hidden) */}
          <canvas
            ref={previewCanvasRef}
            className="hidden"
          />

          {/* Apply Button */}
          <Button
            type="button"
            onClick={handleCropClick}
            disabled={!completedCrop}
            className="w-full"
          >
            <CropIcon className="h-4 w-4 mr-2" />
            Apply Crop
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
