"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Search, Share2, Settings2, AlertCircle, CheckCircle2 } from "lucide-react";

interface SEOData {
  // General SEO
  seo_title: string;
  meta_description: string;
  focus_keyword: string;
  canonical_url: string;
  meta_robots: string;

  // Open Graph
  og_title: string;
  og_description: string;
  og_image: string;
  og_type: string;

  // Twitter Cards
  twitter_card: string;
  twitter_title: string;
  twitter_description: string;
  twitter_image: string;

  // Advanced
  breadcrumb_title: string;
  schema_type: string;
}

interface SEOEditorProps {
  postId?: number;
  postTitle?: string;
  postExcerpt?: string;
  onChange?: (seo: SEOData) => void;
  initialData?: Partial<SEOData>;
}

export function SEOEditor({ postId, postTitle = "", postExcerpt = "", onChange, initialData = {} }: SEOEditorProps) {
  const [seoData, setSEOData] = useState<SEOData>({
    seo_title: initialData.seo_title || "",
    meta_description: initialData.meta_description || "",
    focus_keyword: initialData.focus_keyword || "",
    canonical_url: initialData.canonical_url || "",
    meta_robots: initialData.meta_robots || "",
    og_title: initialData.og_title || "",
    og_description: initialData.og_description || "",
    og_image: initialData.og_image || "",
    og_type: initialData.og_type || "article",
    twitter_card: initialData.twitter_card || "summary_large_image",
    twitter_title: initialData.twitter_title || "",
    twitter_description: initialData.twitter_description || "",
    twitter_image: initialData.twitter_image || "",
    breadcrumb_title: initialData.breadcrumb_title || "",
    schema_type: initialData.schema_type || "Article",
  });

  useEffect(() => {
    onChange?.(seoData);
  }, [seoData]);

  const updateField = (field: keyof SEOData, value: string) => {
    setSEOData(prev => ({ ...prev, [field]: value }));
  };

  // Character count helpers
  const getCharCount = (text: string, limit: number) => {
    const count = text.length;
    const status = count === 0 ? "empty" : count > limit ? "over" : count < limit * 0.5 ? "short" : "good";
    return { count, limit, status };
  };

  const CharCounter = ({ text, limit }: { text: string; limit: number }) => {
    const { count, status } = getCharCount(text, limit);
    const color = status === "good" ? "text-green-600" : status === "over" ? "text-red-600" : "text-amber-600";

    return (
      <div className="flex items-center gap-2 mt-1">
        {status === "good" && <CheckCircle2 className="h-3 w-3 text-green-600" />}
        {status !== "good" && <AlertCircle className="h-3 w-3 text-muted-foreground" />}
        <span className={`text-xs ${color}`}>
          {count} / {limit} characters
        </span>
      </div>
    );
  };

  // Get effective values with fallbacks
  const effectiveSEOTitle = seoData.seo_title || postTitle;
  const effectiveMetaDesc = seoData.meta_description || postExcerpt.slice(0, 160);
  const effectiveOGTitle = seoData.og_title || effectiveSEOTitle;
  const effectiveOGDesc = seoData.og_description || effectiveMetaDesc;
  const effectiveTwitterTitle = seoData.twitter_title || effectiveOGTitle;
  const effectiveTwitterDesc = seoData.twitter_description || effectiveOGDesc;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          SEO & Social Media
        </CardTitle>
        <CardDescription>
          Optimize how your content appears in search engines and social media
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="general">
              <Search className="h-4 w-4 mr-2" />
              General SEO
            </TabsTrigger>
            <TabsTrigger value="social">
              <Share2 className="h-4 w-4 mr-2" />
              Social
            </TabsTrigger>
            <TabsTrigger value="advanced">
              <Settings2 className="h-4 w-4 mr-2" />
              Advanced
            </TabsTrigger>
          </TabsList>

          {/* General SEO Tab */}
          <TabsContent value="general" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="seo-title">SEO Title</Label>
              <Input
                id="seo-title"
                value={seoData.seo_title}
                onChange={(e) => updateField("seo_title", e.target.value)}
                placeholder={postTitle || "Enter SEO title..."}
                maxLength={70}
              />
              <CharCounter text={seoData.seo_title} limit={60} />
              <p className="text-xs text-muted-foreground">
                {seoData.seo_title ? "Using custom SEO title" : `Using post title: "${postTitle}"`}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="meta-description">Meta Description</Label>
              <Textarea
                id="meta-description"
                value={seoData.meta_description}
                onChange={(e) => updateField("meta_description", e.target.value)}
                placeholder={postExcerpt || "Enter meta description..."}
                rows={3}
                maxLength={170}
              />
              <CharCounter text={seoData.meta_description} limit={160} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="focus-keyword">Focus Keyword</Label>
              <Input
                id="focus-keyword"
                value={seoData.focus_keyword}
                onChange={(e) => updateField("focus_keyword", e.target.value)}
                placeholder="Primary keyword for this page..."
              />
              <p className="text-xs text-muted-foreground">
                The main keyword you want this page to rank for
              </p>
            </div>

            {/* Search Preview */}
            <div className="mt-6 p-4 border rounded-lg bg-muted/30">
              <p className="text-xs font-semibold text-muted-foreground mb-2">SEARCH PREVIEW</p>
              <div className="space-y-1">
                <p className="text-lg text-blue-600 hover:underline cursor-pointer">
                  {effectiveSEOTitle}
                </p>
                <p className="text-xs text-green-700">
                  {seoData.canonical_url || "https://example.com/page-url"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {effectiveMetaDesc}
                </p>
              </div>
            </div>
          </TabsContent>

          {/* Social Tab */}
          <TabsContent value="social" className="space-y-6 mt-4">
            {/* Open Graph */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">Open Graph (Facebook, LinkedIn)</h3>
                <Badge variant="outline">Meta Tags</Badge>
              </div>

              <div className="space-y-2">
                <Label htmlFor="og-title">OG Title</Label>
                <Input
                  id="og-title"
                  value={seoData.og_title}
                  onChange={(e) => updateField("og_title", e.target.value)}
                  placeholder={effectiveSEOTitle}
                  maxLength={95}
                />
                <CharCounter text={seoData.og_title} limit={90} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="og-description">OG Description</Label>
                <Textarea
                  id="og-description"
                  value={seoData.og_description}
                  onChange={(e) => updateField("og_description", e.target.value)}
                  placeholder={effectiveMetaDesc}
                  rows={2}
                  maxLength={210}
                />
                <CharCounter text={seoData.og_description} limit={200} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="og-image">OG Image URL</Label>
                <Input
                  id="og-image"
                  value={seoData.og_image}
                  onChange={(e) => updateField("og_image", e.target.value)}
                  placeholder="https://example.com/image.jpg"
                  type="url"
                />
                <p className="text-xs text-muted-foreground">
                  Recommended: 1200x630px (1.91:1 ratio)
                </p>
              </div>
            </div>

            {/* Twitter Cards */}
            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">Twitter Card</h3>
                <Badge variant="outline">Meta Tags</Badge>
              </div>

              <div className="space-y-2">
                <Label htmlFor="twitter-card">Card Type</Label>
                <Select
                  value={seoData.twitter_card}
                  onValueChange={(value) => updateField("twitter_card", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="summary">Summary</SelectItem>
                    <SelectItem value="summary_large_image">Summary with Large Image</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="twitter-title">Twitter Title</Label>
                <Input
                  id="twitter-title"
                  value={seoData.twitter_title}
                  onChange={(e) => updateField("twitter_title", e.target.value)}
                  placeholder={effectiveOGTitle}
                  maxLength={70}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="twitter-description">Twitter Description</Label>
                <Textarea
                  id="twitter-description"
                  value={seoData.twitter_description}
                  onChange={(e) => updateField("twitter_description", e.target.value)}
                  placeholder={effectiveOGDesc}
                  rows={2}
                  maxLength={210}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="twitter-image">Twitter Image URL</Label>
                <Input
                  id="twitter-image"
                  value={seoData.twitter_image}
                  onChange={(e) => updateField("twitter_image", e.target.value)}
                  placeholder={seoData.og_image || "https://example.com/image.jpg"}
                  type="url"
                />
              </div>
            </div>

            {/* Social Preview */}
            <div className="mt-6 p-4 border rounded-lg bg-muted/30">
              <p className="text-xs font-semibold text-muted-foreground mb-3">SOCIAL PREVIEW</p>
              {seoData.og_image && (
                <div className="w-full h-32 bg-muted rounded mb-2 flex items-center justify-center">
                  <img
                    src={seoData.og_image}
                    alt="OG Preview"
                    className="max-w-full max-h-full object-cover rounded"
                  />
                </div>
              )}
              <div className="space-y-1">
                <p className="font-semibold text-sm">{effectiveOGTitle}</p>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {effectiveOGDesc}
                </p>
              </div>
            </div>
          </TabsContent>

          {/* Advanced Tab */}
          <TabsContent value="advanced" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="canonical-url">Canonical URL</Label>
              <Input
                id="canonical-url"
                value={seoData.canonical_url}
                onChange={(e) => updateField("canonical_url", e.target.value)}
                placeholder="https://example.com/canonical-page"
                type="url"
              />
              <p className="text-xs text-muted-foreground">
                Specify the preferred URL if this content exists at multiple URLs
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="schema-type">Schema Type</Label>
              <Select
                value={seoData.schema_type}
                onValueChange={(value) => updateField("schema_type", value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Article">Article</SelectItem>
                  <SelectItem value="BlogPosting">Blog Post</SelectItem>
                  <SelectItem value="NewsArticle">News Article</SelectItem>
                  <SelectItem value="Product">Product</SelectItem>
                  <SelectItem value="Recipe">Recipe</SelectItem>
                  <SelectItem value="Review">Review</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Schema.org structured data type for rich snippets
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="breadcrumb-title">Breadcrumb Title</Label>
              <Input
                id="breadcrumb-title"
                value={seoData.breadcrumb_title}
                onChange={(e) => updateField("breadcrumb_title", e.target.value)}
                placeholder={postTitle || "Custom breadcrumb text"}
              />
              <p className="text-xs text-muted-foreground">
                Custom text to use in breadcrumb navigation
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
