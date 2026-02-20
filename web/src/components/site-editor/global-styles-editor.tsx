"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Save, Palette, Type, Spacing } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ColorPalette {
  name: string;
  slug: string;
  color: string;
}

interface FontSize {
  name: string;
  slug: string;
  size: string;
}

interface GlobalStyles {
  colors?: ColorPalette[];
  fontSizes?: FontSize[];
  spacing?: {
    padding?: string;
    margin?: string;
  };
}

export function GlobalStylesEditor() {
  const [styles, setStyles] = useState<GlobalStyles>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadGlobalStyles();
  }, []);

  const loadGlobalStyles = async () => {
    try {
      setIsLoading(true);
      const response = await fetch("/api/global-styles");

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.success === false) {
        // Not yet implemented - use default values
        setStyles({
          colors: [
            { name: "Primary", slug: "primary", color: "#0073aa" },
            { name: "Secondary", slug: "secondary", color: "#23282d" },
            { name: "Accent", slug: "accent", color: "#00a0d2" },
          ],
          fontSizes: [
            { name: "Small", slug: "small", size: "14px" },
            { name: "Medium", slug: "medium", size: "16px" },
            { name: "Large", slug: "large", size: "20px" },
            { name: "Extra Large", slug: "x-large", size: "28px" },
          ],
          spacing: {
            padding: "20px",
            margin: "20px",
          },
        });
      } else {
        setStyles(result);
      }
    } catch (error) {
      console.error("Failed to load global styles:", error);
      toast({
        variant: "destructive",
        title: "Error loading styles",
        description: error instanceof Error ? error.message : "Failed to load global styles",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);

      const response = await fetch("/api/global-styles", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(styles),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.success === false) {
        toast({
          variant: "destructive",
          title: "Feature not available",
          description: result.message || "Global styles editing requires WordPress REST API integration.",
        });
        return;
      }

      setIsDirty(false);
      toast({
        title: "Styles saved",
        description: "Global styles have been saved to theme.json",
      });
    } catch (error) {
      console.error("Failed to save global styles:", error);
      toast({
        variant: "destructive",
        title: "Error saving styles",
        description: error instanceof Error ? error.message : "Failed to save global styles",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const updateColor = (index: number, field: keyof ColorPalette, value: string) => {
    const newColors = [...(styles.colors || [])];
    newColors[index] = { ...newColors[index], [field]: value };
    setStyles({ ...styles, colors: newColors });
    setIsDirty(true);
  };

  const updateFontSize = (index: number, field: keyof FontSize, value: string) => {
    const newFontSizes = [...(styles.fontSizes || [])];
    newFontSizes[index] = { ...newFontSizes[index], [field]: value };
    setStyles({ ...styles, fontSizes: newFontSizes });
    setIsDirty(true);
  };

  const addColor = () => {
    const newColors = [...(styles.colors || [])];
    newColors.push({ name: "New Color", slug: "new-color", color: "#000000" });
    setStyles({ ...styles, colors: newColors });
    setIsDirty(true);
  };

  const addFontSize = () => {
    const newFontSizes = [...(styles.fontSizes || [])];
    newFontSizes.push({ name: "New Size", slug: "new-size", size: "16px" });
    setStyles({ ...styles, fontSizes: newFontSizes });
    setIsDirty(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading global styles...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b bg-muted/20 px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="font-semibold">Global Styles</h2>
          <p className="text-xs text-muted-foreground">
            Edit theme.json settings for your WordPress theme
          </p>
          {isDirty && (
            <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded mt-1 inline-block">
              Unsaved changes
            </span>
          )}
        </div>

        <Button size="sm" onClick={handleSave} disabled={!isDirty || isSaving}>
          <Save className="h-4 w-4 mr-1" />
          {isSaving ? "Saving..." : "Save"}
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 max-w-4xl mx-auto space-y-6">
          <Tabs defaultValue="colors">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="colors">
                <Palette className="h-4 w-4 mr-2" />
                Colors
              </TabsTrigger>
              <TabsTrigger value="typography">
                <Type className="h-4 w-4 mr-2" />
                Typography
              </TabsTrigger>
              <TabsTrigger value="spacing">
                <Spacing className="h-4 w-4 mr-2" />
                Spacing
              </TabsTrigger>
            </TabsList>

            {/* Colors Tab */}
            <TabsContent value="colors" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Color Palette</CardTitle>
                  <CardDescription>
                    Define the color palette for your theme
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {styles.colors?.map((color, index) => (
                    <div key={index} className="flex items-center gap-4">
                      <div className="flex-1">
                        <Label>Name</Label>
                        <Input
                          value={color.name}
                          onChange={(e) => updateColor(index, "name", e.target.value)}
                          placeholder="Color name"
                        />
                      </div>
                      <div className="flex-1">
                        <Label>Slug</Label>
                        <Input
                          value={color.slug}
                          onChange={(e) => updateColor(index, "slug", e.target.value)}
                          placeholder="color-slug"
                        />
                      </div>
                      <div className="w-24">
                        <Label>Color</Label>
                        <div className="flex items-center gap-2">
                          <Input
                            type="color"
                            value={color.color}
                            onChange={(e) => updateColor(index, "color", e.target.value)}
                            className="h-10 w-full"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  <Button onClick={addColor} variant="outline" className="w-full">
                    Add Color
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Typography Tab */}
            <TabsContent value="typography" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Font Sizes</CardTitle>
                  <CardDescription>
                    Define font size presets for your theme
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {styles.fontSizes?.map((fontSize, index) => (
                    <div key={index} className="flex items-center gap-4">
                      <div className="flex-1">
                        <Label>Name</Label>
                        <Input
                          value={fontSize.name}
                          onChange={(e) => updateFontSize(index, "name", e.target.value)}
                          placeholder="Size name"
                        />
                      </div>
                      <div className="flex-1">
                        <Label>Slug</Label>
                        <Input
                          value={fontSize.slug}
                          onChange={(e) => updateFontSize(index, "slug", e.target.value)}
                          placeholder="size-slug"
                        />
                      </div>
                      <div className="w-24">
                        <Label>Size</Label>
                        <Input
                          value={fontSize.size}
                          onChange={(e) => updateFontSize(index, "size", e.target.value)}
                          placeholder="16px"
                        />
                      </div>
                    </div>
                  ))}
                  <Button onClick={addFontSize} variant="outline" className="w-full">
                    Add Font Size
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Spacing Tab */}
            <TabsContent value="spacing" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Spacing</CardTitle>
                  <CardDescription>
                    Define default spacing values
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Default Padding</Label>
                    <Input
                      value={styles.spacing?.padding || ""}
                      onChange={(e) => {
                        setStyles({
                          ...styles,
                          spacing: { ...styles.spacing, padding: e.target.value },
                        });
                        setIsDirty(true);
                      }}
                      placeholder="20px"
                    />
                  </div>
                  <div>
                    <Label>Default Margin</Label>
                    <Input
                      value={styles.spacing?.margin || ""}
                      onChange={(e) => {
                        setStyles({
                          ...styles,
                          spacing: { ...styles.spacing, margin: e.target.value },
                        });
                        setIsDirty(true);
                      }}
                      placeholder="20px"
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Info Card */}
          <Card className="bg-muted/30">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                <strong>Note:</strong> Global styles editing modifies your theme's theme.json file.
                Changes will apply across all templates and blocks that use these settings.
                This feature requires WordPress REST API integration to be fully functional.
              </p>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
