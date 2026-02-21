"use client";

import { useEffect, useState } from "react";
import { useTemplateStore } from "@/stores/template-store";
import { Loader2 } from "lucide-react";

interface TemplatePreviewProps {
  templateId: number;
}

export function TemplatePreview({ templateId }: TemplatePreviewProps) {
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentTemplate = useTemplateStore((s: any) => s.currentTemplate);

  useEffect(() => {
    if (!currentTemplate) return;

    const loadPreview = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // For now, render the template content directly in an iframe
        // In the future, this could call a WordPress endpoint that renders
        // the template with the active theme
        const html = `
          <!DOCTYPE html>
          <html>
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <style>
                body {
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                  line-height: 1.6;
                  color: #333;
                  max-width: 800px;
                  margin: 0 auto;
                  padding: 20px;
                }
                h1, h2, h3, h4, h5, h6 {
                  margin-top: 1.5em;
                  margin-bottom: 0.5em;
                }
                p {
                  margin-bottom: 1em;
                }
                img {
                  max-width: 100%;
                  height: auto;
                }
              </style>
            </head>
            <body>
              ${currentTemplate.content || "<p>Empty template</p>"}
            </body>
          </html>
        `;

        setPreviewHtml(html);
      } catch (err) {
        console.error("Failed to load preview:", err);
        setError(err instanceof Error ? err.message : "Failed to load preview");
      } finally {
        setIsLoading(false);
      }
    };

    loadPreview();
  }, [currentTemplate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading preview...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-destructive">
          <p className="font-medium">Preview Error</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <iframe
      className="w-full h-full border-0"
      sandbox="allow-same-origin allow-scripts"
      srcDoc={previewHtml}
      title="Template Preview"
    />
  );
}
