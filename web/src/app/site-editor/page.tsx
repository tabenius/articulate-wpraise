"use client";

import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode2, Layout, Palette } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Template {
  id: number;
  title: string;
  slug: string;
  content: string;
}

interface TemplatePart {
  id: number;
  title: string;
  slug: string;
  content: string;
}

export default function SiteEditorPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateParts, setTemplateParts] = useState<TemplatePart[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    loadTemplates();
    loadTemplateParts();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/templates");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setTemplates(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load templates:", error);
      toast({
        variant: "destructive",
        title: "Error loading templates",
        description:
          error instanceof Error ? error.message : "Failed to load templates",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadTemplateParts = async () => {
    try {
      const response = await fetch("/api/template-parts");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setTemplateParts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load template parts:", error);
      toast({
        variant: "destructive",
        title: "Error loading template parts",
        description:
          error instanceof Error
            ? error.message
            : "Failed to load template parts",
      });
    }
  };

  const handleSelectTemplate = async (template: Template) => {
    setSelectedTemplate(template);
    toast({
      title: "Template selected",
      description: `Loaded "${template.title}"`,
    });
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-muted/30 px-4 py-3">
        <h1 className="text-2xl font-bold">Site Editor</h1>
        <p className="text-sm text-muted-foreground">
          Edit templates, template parts, and global styles
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-80 border-r bg-muted/10">
          <Tabs defaultValue="templates" className="h-full flex flex-col">
            <TabsList className="mx-4 mt-4">
              <TabsTrigger value="templates" className="flex-1">
                <Layout className="h-4 w-4 mr-2" />
                Templates
              </TabsTrigger>
              <TabsTrigger value="parts" className="flex-1">
                <FileCode2 className="h-4 w-4 mr-2" />
                Parts
              </TabsTrigger>
            </TabsList>

            <TabsContent value="templates" className="flex-1 mt-4">
              <ScrollArea className="h-full px-4">
                {loading ? (
                  <div className="text-sm text-muted-foreground">
                    Loading templates...
                  </div>
                ) : templates.length === 0 ? (
                  <div className="text-sm text-muted-foreground">
                    No templates found. Your theme may not support Full Site
                    Editing.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {templates.map((template) => (
                      <Button
                        key={template.id}
                        variant={
                          selectedTemplate?.id === template.id
                            ? "default"
                            : "ghost"
                        }
                        className="w-full justify-start"
                        onClick={() => handleSelectTemplate(template)}
                      >
                        <Layout className="h-4 w-4 mr-2" />
                        <div className="flex-1 text-left truncate">
                          <div className="font-medium truncate">
                            {template.title}
                          </div>
                          <div className="text-xs text-muted-foreground truncate">
                            {template.slug}
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="parts" className="flex-1 mt-4">
              <ScrollArea className="h-full px-4">
                {templateParts.length === 0 ? (
                  <div className="text-sm text-muted-foreground">
                    No template parts found.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {templateParts.map((part) => (
                      <Button
                        key={part.id}
                        variant="ghost"
                        className="w-full justify-start"
                      >
                        <FileCode2 className="h-4 w-4 mr-2" />
                        <div className="flex-1 text-left truncate">
                          <div className="font-medium truncate">{part.title}</div>
                          <div className="text-xs text-muted-foreground truncate">
                            {part.slug}
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {selectedTemplate ? (
            <>
              {/* Template Editor Toolbar */}
              <div className="border-b bg-muted/20 px-4 py-3">
                <h2 className="font-semibold">{selectedTemplate.title}</h2>
                <p className="text-xs text-muted-foreground">
                  {selectedTemplate.slug}
                </p>
              </div>

              {/* Template Editor */}
              <ScrollArea className="flex-1">
                <div className="p-8 max-w-4xl mx-auto">
                  <div className="bg-muted/30 rounded-lg p-4 font-mono text-sm">
                    <pre className="whitespace-pre-wrap">
                      {selectedTemplate.content || "No content"}
                    </pre>
                  </div>
                  <div className="mt-4 text-sm text-muted-foreground">
                    <p>
                      Template editing is currently read-only. Future updates will
                      enable full block editing.
                    </p>
                  </div>
                </div>
              </ScrollArea>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground max-w-md">
                <Palette className="h-16 w-16 mx-auto mb-4 opacity-40" />
                <h3 className="text-lg font-semibold mb-2">
                  WordPress Site Editor
                </h3>
                <p className="text-sm">
                  Select a template or template part from the sidebar to start
                  editing.
                </p>
                <div className="mt-6 text-xs space-y-1">
                  <p>
                    <strong>Templates</strong> control the layout of different page
                    types
                  </p>
                  <p>
                    <strong>Template Parts</strong> are reusable components like
                    headers and footers
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
