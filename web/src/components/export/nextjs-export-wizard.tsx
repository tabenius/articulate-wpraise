"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Download, Rocket, Settings2, FileCode, Image as ImageIcon, Loader2, CheckCircle2 } from "lucide-react";

type ContentFormat = "react" | "blocks" | "mdx" | "html";
type RenderStrategy = "ssg" | "ssr" | "isr" | "headless";
type MediaStrategy = "download" | "keep_urls" | "cdn" | "next_image";

type ExportStep = "configure" | "exporting" | "complete";

export function NextJSExportWizard() {
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState<ExportStep>("configure");
  const [progress, setProgress] = useState(0);

  // Configuration state
  const [contentFormat, setContentFormat] = useState<ContentFormat>("react");
  const [renderStrategy, setRenderStrategy] = useState<RenderStrategy>("ssg");
  const [mediaStrategy, setMediaStrategy] = useState<MediaStrategy>("download");

  // Export result
  const [exportResult, setExportResult] = useState<any>(null);

  async function startExport() {
    setCurrentStep("exporting");
    setProgress(0);

    try {
      const sessionId = localStorage.getItem("sessionId");
      const activeConnectionId = localStorage.getItem("activeConnectionId");

      if (!sessionId || !activeConnectionId) {
        throw new Error("No connection selected");
      }

      // Step 1: Export content (30%)
      setProgress(10);
      toast({
        title: "Exporting content...",
        description: "Fetching posts, pages, and media from WordPress",
      });

      // Step 2: Generate Next.js project (60%)
      setProgress(30);
      toast({
        title: "Generating Next.js project...",
        description: "Creating project structure and components",
      });

      const response = await fetch("http://localhost:8000/mcp/call-tool", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          tool_name: "generate_nextjs_site",
          arguments: {
            content_format: contentFormat,
            render_strategy: renderStrategy,
            media_strategy: mediaStrategy,
            context: { connection_id: parseInt(activeConnectionId) },
          },
        }),
      });

      setProgress(60);

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Export failed");
      }

      // Step 3: Complete (100%)
      setProgress(90);
      toast({
        title: "Finalizing export...",
        description: "Creating zip archive",
      });

      setProgress(100);
      setExportResult(data);
      setCurrentStep("complete");

      toast({
        title: "Export complete!",
        description: `Created ${data.files_created} files`,
      });
    } catch (error) {
      toast({
        title: "Export failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
      setCurrentStep("configure");
    }
  }

  async function downloadExport() {
    if (!exportResult || !exportResult.zip_file) {
      toast({
        title: "No export available",
        description: "Please run the export first",
        variant: "destructive",
      });
      return;
    }

    // TODO: Implement download of zip file from server
    toast({
      title: "Download started",
      description: "Your Next.js project is being downloaded",
    });
  }

  function resetWizard() {
    setCurrentStep("configure");
    setProgress(0);
    setExportResult(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Rocket className="h-5 w-5" />
          Export to Next.js
        </CardTitle>
        <CardDescription>
          Convert your WordPress site to a modern Next.js application
        </CardDescription>
      </CardHeader>
      <CardContent>
        {currentStep === "configure" && (
          <div className="space-y-6">
            {/* Content Format */}
            <div className="space-y-3">
              <Label className="flex items-center gap-2">
                <FileCode className="h-4 w-4" />
                Content Format
              </Label>
              <Select value={contentFormat} onValueChange={(v) => setContentFormat(v as ContentFormat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="react">
                    <div>
                      <div className="font-semibold">React Components (Recommended)</div>
                      <div className="text-xs text-muted-foreground">Convert blocks to clean React components</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="blocks">
                    <div>
                      <div className="font-semibold">WordPress Blocks</div>
                      <div className="text-xs text-muted-foreground">Use @wordpress/block-library renderer</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="mdx">
                    <div>
                      <div className="font-semibold">MDX Format</div>
                      <div className="text-xs text-muted-foreground">Convert to MDX for easy editing</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="html">
                    <div>
                      <div className="font-semibold">Keep as HTML</div>
                      <div className="text-xs text-muted-foreground">Render via dangerouslySetInnerHTML</div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Rendering Strategy */}
            <div className="space-y-3">
              <Label className="flex items-center gap-2">
                <Settings2 className="h-4 w-4" />
                Rendering Strategy
              </Label>
              <Select value={renderStrategy} onValueChange={(v) => setRenderStrategy(v as RenderStrategy)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ssg">
                    <div>
                      <div className="font-semibold">Static Generation (SSG) - Recommended</div>
                      <div className="text-xs text-muted-foreground">Fully static HTML, best performance</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="ssr">
                    <div>
                      <div className="font-semibold">Server-Side Rendering (SSR)</div>
                      <div className="text-xs text-muted-foreground">Render on each request</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="isr">
                    <div>
                      <div className="font-semibold">Incremental Static Regeneration (ISR)</div>
                      <div className="text-xs text-muted-foreground">Static with periodic updates</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="headless">
                    <div>
                      <div className="font-semibold">Headless CMS</div>
                      <div className="text-xs text-muted-foreground">Fetch from WordPress at runtime</div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Media Strategy */}
            <div className="space-y-3">
              <Label className="flex items-center gap-2">
                <ImageIcon className="h-4 w-4" />
                Media Strategy
              </Label>
              <Select value={mediaStrategy} onValueChange={(v) => setMediaStrategy(v as MediaStrategy)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="download">
                    <div>
                      <div className="font-semibold">Download & Bundle (Recommended)</div>
                      <div className="text-xs text-muted-foreground">All media in Next.js public folder</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="next_image">
                    <div>
                      <div className="font-semibold">Next.js Image Optimization</div>
                      <div className="text-xs text-muted-foreground">Download + automatic optimization</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="keep_urls">
                    <div>
                      <div className="font-semibold">Keep WordPress URLs</div>
                      <div className="text-xs text-muted-foreground">Reference original URLs (requires WordPress)</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="cdn">
                    <div>
                      <div className="font-semibold">Upload to CDN</div>
                      <div className="text-xs text-muted-foreground">Migrate to Cloudflare/Vercel</div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Export Button */}
            <Button onClick={startExport} className="w-full" size="lg">
              <Rocket className="h-4 w-4 mr-2" />
              Start Export
            </Button>

            {/* Configuration Preview */}
            <div className="mt-6 p-4 border rounded-lg bg-muted/30">
              <h4 className="font-semibold mb-2">Export Configuration</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Content Format:</span>
                  <span className="font-medium">{contentFormat.toUpperCase()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rendering:</span>
                  <span className="font-medium">{renderStrategy.toUpperCase()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Media:</span>
                  <span className="font-medium">
                    {mediaStrategy === "next_image" ? "Next.js Optimized" : mediaStrategy.replace("_", " ")}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {currentStep === "exporting" && (
          <div className="space-y-6 py-8">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <div className="text-center">
                <h3 className="text-lg font-semibold">Exporting your site...</h3>
                <p className="text-sm text-muted-foreground">This may take a few minutes</p>
              </div>
            </div>

            <Progress value={progress} className="w-full" />

            <div className="text-center text-sm text-muted-foreground">
              {progress}% complete
            </div>
          </div>
        )}

        {currentStep === "complete" && exportResult && (
          <div className="space-y-6">
            <div className="flex flex-col items-center gap-4 py-6">
              <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold">Export Complete!</h3>
                <p className="text-sm text-muted-foreground">Your Next.js site is ready</p>
              </div>
            </div>

            {/* Export Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold">{exportResult.files_created}</div>
                <div className="text-sm text-muted-foreground">Files Created</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-2xl font-bold">{contentFormat.toUpperCase()}</div>
                <div className="text-sm text-muted-foreground">Format</div>
              </div>
            </div>

            {/* Export Details */}
            <div className="p-4 border rounded-lg bg-muted/30 space-y-2">
              <h4 className="font-semibold">Export Details</h4>
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Content Format:</span>
                  <span>{contentFormat}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rendering:</span>
                  <span>{renderStrategy}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Media Strategy:</span>
                  <span>{mediaStrategy}</span>
                </div>
                {exportResult.output_dir && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Output:</span>
                    <span className="font-mono text-xs">{exportResult.output_dir}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button onClick={downloadExport} className="flex-1" size="lg">
                <Download className="h-4 w-4 mr-2" />
                Download Project
              </Button>
              <Button onClick={resetWizard} variant="outline" size="lg">
                New Export
              </Button>
            </div>

            {/* Next Steps */}
            <div className="p-4 border rounded-lg bg-blue-50 dark:bg-blue-950">
              <h4 className="font-semibold mb-2">Next Steps</h4>
              <ol className="text-sm space-y-1 list-decimal list-inside">
                <li>Download and extract the zip file</li>
                <li>Run <code className="bg-white dark:bg-gray-800 px-1 rounded">npm install</code></li>
                <li>Run <code className="bg-white dark:bg-gray-800 px-1 rounded">npm run dev</code> to preview</li>
                <li>Run <code className="bg-white dark:bg-gray-800 px-1 rounded">npm run build</code> for production</li>
                <li>Deploy to Vercel, Netlify, or any static host</li>
              </ol>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
