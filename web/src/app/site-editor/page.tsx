"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode2, Layout, Palette, Search, Star, Clock, Grid3x3, List } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useTemplateStore } from "@/stores/template-store";
import { TemplateEditor } from "@/components/site-editor/template-editor";
import { CreateTemplateDialog } from "@/components/site-editor/create-template-dialog";
import { GlobalStylesEditor } from "@/components/site-editor/global-styles-editor";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { TemplateListSkeleton } from "@/components/skeletons/template-list-skeleton";
import { handleConnectionError } from "@/lib/error-helpers";

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
  const [activeTab, setActiveTab] = useState<"recent" | "templates" | "parts" | "styles">("recent");
  const [currentTemplatePart, setCurrentTemplatePart] = useState<TemplatePart | null>(null);
  const [templateSearch, setTemplateSearch] = useState("");
  const [partSearch, setPartSearch] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const templates = useTemplateStore((s) => s.templates);
  const templateParts = useTemplateStore((s) => s.templateParts);
  const currentTemplate = useTemplateStore((s) => s.currentTemplate);
  const favorites = useTemplateStore((s) => s.favorites);
  const recentTemplates = useTemplateStore((s) => s.recentTemplates);
  const toggleFavorite = useTemplateStore((s) => s.toggleFavorite);
  const getPartUsage = useTemplateStore((s) => s.getPartUsage);
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
      handleConnectionError(error, loadTemplates);
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
      handleConnectionError(error, loadTemplateParts);
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
            onValueChange={(value) => setActiveTab(value as "recent" | "templates" | "parts" | "styles")}
            className="h-full flex flex-col"
          >
            <TabsList className="mx-4 mt-4 grid grid-cols-4">
              <TabsTrigger value="recent">
                <Clock className="h-4 w-4 mr-1" />
                Recent
              </TabsTrigger>
              <TabsTrigger value="templates">
                <Layout className="h-4 w-4 mr-1" />
                Templates
              </TabsTrigger>
              <TabsTrigger value="parts">
                <FileCode2 className="h-4 w-4 mr-1" />
                Parts
              </TabsTrigger>
              <TabsTrigger value="styles">
                <Palette className="h-4 w-4 mr-1" />
                Styles
              </TabsTrigger>
            </TabsList>

            <TabsContent value="recent" className="flex-1 mt-4">
              <ScrollArea className="h-full">
                {/* Favorites Section */}
                {favorites.length > 0 && (
                  <div className="px-4 mb-6">
                    <h3 className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                      <Star className="h-3 w-3 fill-current" />
                      FAVORITES
                    </h3>
                    <div className="space-y-2">
                      {templates
                        .filter((t) => favorites.includes(t.id))
                        .map((template) => (
                          <div key={template.id} className="relative group">
                            <Button
                              variant={
                                currentTemplate?.id === template.id
                                  ? "default"
                                  : "ghost"
                              }
                              className="w-full justify-start pr-8"
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
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleFavorite(template.id);
                              }}
                              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-100"
                            >
                              <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                            </button>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Recent Section */}
                <div className="px-4">
                  <h3 className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    RECENTLY EDITED
                  </h3>
                  {recentTemplates.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-4">
                      No recent templates yet
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {templates
                        .filter((t) => recentTemplates.includes(t.id))
                        .sort((a, b) => recentTemplates.indexOf(a.id) - recentTemplates.indexOf(b.id))
                        .map((template) => (
                          <div key={template.id} className="relative group">
                            <Button
                              variant={
                                currentTemplate?.id === template.id
                                  ? "default"
                                  : "ghost"
                              }
                              className="w-full justify-start pr-8"
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
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleFavorite(template.id);
                              }}
                              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <Star
                                className={`h-4 w-4 ${
                                  favorites.includes(template.id)
                                    ? "fill-yellow-500 text-yellow-500"
                                    : "text-muted-foreground"
                                }`}
                              />
                            </button>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="templates" className="flex-1 mt-4">
              <div className="px-4 pb-3">
                <div className="flex items-center gap-2 mb-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="Search templates..."
                      value={templateSearch}
                      onChange={(e) => setTemplateSearch(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                  <div className="flex items-center gap-1 border rounded-md p-1">
                    <Button
                      variant={viewMode === "list" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setViewMode("list")}
                      className="h-7 w-7 p-0"
                      title="List view"
                    >
                      <List className="h-4 w-4" />
                    </Button>
                    <Button
                      variant={viewMode === "grid" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setViewMode("grid")}
                      className="h-7 w-7 p-0"
                      title="Grid view"
                    >
                      <Grid3x3 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {templateSearch && (
                  <p className="text-xs text-muted-foreground">
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
                ) : viewMode === "grid" ? (
                  <div className="grid grid-cols-2 gap-3 px-4">
                    {filteredTemplates.map((template) => (
                      <div
                        key={template.id}
                        className={`relative group cursor-pointer border rounded-lg p-4 hover:bg-muted/50 transition-colors ${
                          currentTemplate?.id === template.id
                            ? "border-primary bg-primary/5"
                            : "border-muted"
                        }`}
                        onClick={() => handleSelectTemplate(template)}
                      >
                        <div className="flex flex-col items-center text-center gap-2">
                          <div className={`p-3 rounded-lg ${
                            currentTemplate?.id === template.id
                              ? "bg-primary/10"
                              : "bg-muted"
                          }`}>
                            <Layout className={`h-8 w-8 ${
                              currentTemplate?.id === template.id
                                ? "text-primary"
                                : "text-muted-foreground"
                            }`} />
                          </div>
                          <div className="flex-1 min-w-0 w-full">
                            <div className="font-medium truncate text-sm">
                              {template.title}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {template.slug}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFavorite(template.id);
                          }}
                          className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Star
                            className={`h-4 w-4 ${
                              favorites.includes(template.id)
                                ? "fill-yellow-500 text-yellow-500"
                                : "text-muted-foreground"
                            }`}
                          />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2 px-4">
                    {filteredTemplates.map((template) => (
                      <div key={template.id} className="relative group">
                        <Button
                          variant={
                            currentTemplate?.id === template.id
                              ? "default"
                              : "ghost"
                          }
                          className="w-full justify-start pr-8"
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
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFavorite(template.id);
                          }}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Star
                            className={`h-4 w-4 ${
                              favorites.includes(template.id)
                                ? "fill-yellow-500 text-yellow-500"
                                : "text-muted-foreground"
                            }`}
                          />
                        </button>
                      </div>
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
                    {filteredTemplateParts.map((part) => {
                      const usage = getPartUsage(part.slug);
                      const usageCount = usage.length;
                      return (
                        <div key={part.id} className="relative group">
                          <Button
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
                                {usageCount > 0 && (
                                  <span className="ml-2 text-primary">
                                    • Used in {usageCount} template{usageCount !== 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>
                            </div>
                          </Button>
                        </div>
                      );
                    })}
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
