"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode2, Layout, Palette, Search } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useTemplateStore } from "@/stores/template-store";
import { TemplateEditor } from "@/components/site-editor/template-editor";
import { CreateTemplateDialog } from "@/components/site-editor/create-template-dialog";
import { GlobalStylesEditor } from "@/components/site-editor/global-styles-editor";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { TemplateListSkeleton } from "@/components/skeletons/template-list-skeleton";

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
  const [activeTab, setActiveTab] = useState<"templates" | "parts" | "styles">("templates");
  const [currentTemplatePart, setCurrentTemplatePart] = useState<TemplatePart | null>(null);
  const [templateSearch, setTemplateSearch] = useState("");
  const [partSearch, setPartSearch] = useState("");
  const templates = useTemplateStore((s) => s.templates);
  const templateParts = useTemplateStore((s) => s.templateParts);
  const currentTemplate = useTemplateStore((s) => s.currentTemplate);
  const setTemplates = useTemplateStore((s) => s.setTemplates);
  const setTemplateParts = useTemplateStore((s) => s.setTemplateParts);
  const setCurrentTemplate = useTemplateStore((s) => s.setCurrentTemplate);
  const isLoading = useTemplateStore((s) => s.isLoading);
  const setLoading = useTemplateStore((s) => s.setLoading);
  const { toast} = useToast();

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
    setCurrentTemplate(template);
    setCurrentTemplatePart(null);
    toast({
      title: "Template selected",
      description: `Loaded "${template.title}"`,
    });
  };

  const handleSelectTemplatePart = async (part: TemplatePart) => {
    setCurrentTemplatePart(part);
    setCurrentTemplate(null);
    toast({
      title: "Template part selected",
      description: `Loaded "${part.title}"`,
    });
  };

  // Filter templates based on search
  const filteredTemplates = templates.filter((template) => {
    const searchLower = templateSearch.toLowerCase();
    return (
      template.title.toLowerCase().includes(searchLower) ||
      template.slug.toLowerCase().includes(searchLower)
    );
  });

  // Filter template parts based on search
  const filteredTemplateParts = templateParts.filter((part) => {
    const searchLower = partSearch.toLowerCase();
    return (
      part.title.toLowerCase().includes(searchLower) ||
      part.slug.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-muted/30 px-4 py-3">
        <div className="mb-3">
          <Breadcrumbs
            items={[
              { label: "Home", href: "/" },
              { label: "Site Editor" },
            ]}
          />
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Site Editor</h1>
            <p className="text-sm text-muted-foreground">
              Edit templates, template parts, and global styles
            </p>
          </div>
          <CreateTemplateDialog
            onTemplateCreated={async (template) => {
              await loadTemplates();
              setCurrentTemplate(template as any);
            }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-80 border-r bg-muted/10">
          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as "templates" | "parts" | "styles")}
            className="h-full flex flex-col"
          >
            <TabsList className="mx-4 mt-4 grid grid-cols-3">
              <TabsTrigger value="templates">
                <Layout className="h-4 w-4 mr-2" />
                Templates
              </TabsTrigger>
              <TabsTrigger value="parts">
                <FileCode2 className="h-4 w-4 mr-2" />
                Parts
              </TabsTrigger>
              <TabsTrigger value="styles">
                <Palette className="h-4 w-4 mr-2" />
                Styles
              </TabsTrigger>
            </TabsList>

            <TabsContent value="templates" className="flex-1 mt-4">
              <div className="px-4 pb-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Search templates..."
                    value={templateSearch}
                    onChange={(e) => setTemplateSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>
                {templateSearch && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''} found
                  </p>
                )}
              </div>
              <ScrollArea className="h-full">
                {isLoading ? (
                  <TemplateListSkeleton />
                ) : filteredTemplates.length === 0 ? (
                  <div className="px-4 text-sm text-muted-foreground">
                    {templateSearch
                      ? `No templates match "${templateSearch}"`
                      : "No templates found. Your theme may not support Full Site Editing."}
                  </div>
                ) : (
                  <div className="space-y-2 px-4">
                    {filteredTemplates.map((template) => (
                      <Button
                        key={template.id}
                        variant={
                          currentTemplate?.id === template.id
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
              <div className="px-4 pb-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Search template parts..."
                    value={partSearch}
                    onChange={(e) => setPartSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>
                {partSearch && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {filteredTemplateParts.length} part{filteredTemplateParts.length !== 1 ? 's' : ''} found
                  </p>
                )}
              </div>
              <ScrollArea className="h-full">
                {filteredTemplateParts.length === 0 ? (
                  <div className="px-4 text-sm text-muted-foreground">
                    {partSearch
                      ? `No template parts match "${partSearch}"`
                      : "No template parts found."}
                  </div>
                ) : (
                  <div className="space-y-2 px-4">
                    {filteredTemplateParts.map((part) => (
                      <Button
                        key={part.id}
                        variant={
                          currentTemplatePart?.id === part.id
                            ? "default"
                            : "ghost"
                        }
                        className="w-full justify-start"
                        onClick={() => handleSelectTemplatePart(part)}
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

            <TabsContent value="styles" className="flex-1 mt-4">
              <ScrollArea className="h-full px-4">
                <div className="text-sm text-muted-foreground">
                  Click on Global Styles to edit theme colors, typography, and
                  spacing.
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        {/* Main Content */}
        {activeTab === "styles" ? (
          <GlobalStylesEditor />
        ) : currentTemplate ? (
          <TemplateEditor
            templateId={currentTemplate.id}
            type="template"
            onSave={() => {
              toast({
                title: "Template saved",
                description: `"${currentTemplate.title}" has been saved to WordPress`,
              });
            }}
          />
        ) : currentTemplatePart ? (
          <TemplateEditor
            templateId={currentTemplatePart.id}
            type="part"
            onSave={() => {
              toast({
                title: "Template part saved",
                description: `"${currentTemplatePart.title}" has been saved to WordPress`,
              });
            }}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-2xl">
              <div className="mb-6 relative">
                <Palette className="h-20 w-20 mx-auto text-primary/20" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Layout className="h-10 w-10 text-primary/40" />
                </div>
              </div>

              <h3 className="text-2xl font-bold mb-3 text-foreground">
                WordPress Site Editor
              </h3>
              <p className="text-base text-muted-foreground mb-8">
                Build and customize your WordPress theme with a visual editor for templates, template parts, and global styles.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="p-4 rounded-lg bg-muted/30 border border-muted text-left">
                  <Layout className="h-6 w-6 text-primary mb-2" />
                  <h4 className="font-semibold text-sm mb-1">Templates</h4>
                  <p className="text-xs text-muted-foreground">
                    Control the layout of different page types like homepage, blog posts, and pages
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-muted/30 border border-muted text-left">
                  <FileCode2 className="h-6 w-6 text-primary mb-2" />
                  <h4 className="font-semibold text-sm mb-1">Template Parts</h4>
                  <p className="text-xs text-muted-foreground">
                    Create reusable components like headers, footers, and sidebars
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-muted/30 border border-muted text-left">
                  <Palette className="h-6 w-6 text-primary mb-2" />
                  <h4 className="font-semibold text-sm mb-1">Global Styles</h4>
                  <p className="text-xs text-muted-foreground">
                    Customize theme colors, typography, spacing, and design settings
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-center gap-3">
                <Button
                  variant="default"
                  onClick={() => setActiveTab("templates")}
                  className="gap-2"
                >
                  <Layout className="h-4 w-4" />
                  Browse Templates
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setActiveTab("styles")}
                  className="gap-2"
                >
                  <Palette className="h-4 w-4" />
                  Edit Global Styles
                </Button>
              </div>

              <p className="text-xs text-muted-foreground mt-6">
                💡 <strong>Tip:</strong> Use the search bar to quickly find templates, or create a new one with the "+" button
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
