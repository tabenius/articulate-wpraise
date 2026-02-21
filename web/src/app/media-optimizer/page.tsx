"use client";

import { ImageOptimizer } from "@/components/media/image-optimizer";

export default function MediaOptimizerPage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Media Optimizer</h1>
          <p className="text-muted-foreground mt-2">
            Compress, resize, and optimize images for faster page load times and better SEO
          </p>
        </div>

        <ImageOptimizer />
      </div>
    </div>
  );
}
