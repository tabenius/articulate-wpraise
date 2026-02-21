"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Sparkles, Save, RotateCcw } from "lucide-react";

interface AIPreferences {
  tone: string;
  audience: string;
  writing_level: string;
  content_length: string;
  auto_generate_seo: boolean;
  seo_style: string;
  target_keyword_density: number;
  primary_language: string;
  translation_languages: string[];
  brand_voice: string | null;
  company_values: string[];
  avoid_words: string[];
  preferred_terms: Record<string, string>;
  auto_generate_alt_text: boolean;
  alt_text_style: string;
  suggestion_frequency: string;
  confirm_before_apply: boolean;
  dismissed_suggestions: string[];
  default_model: string;
  model_config: {
    chat: string;
    content_generation: string;
    seo_optimization: string;
    content_analysis: string;
    image_analysis: string;
  };
  use_emojis: boolean;
  include_sources: boolean;
}

const DEFAULT_PREFERENCES: AIPreferences = {
  tone: "professional",
  audience: "general",
  writing_level: "moderate",
  content_length: "medium",
  auto_generate_seo: false,
  seo_style: "balanced",
  target_keyword_density: 1.5,
  primary_language: "en",
  translation_languages: [],
  brand_voice: null,
  company_values: [],
  avoid_words: [],
  preferred_terms: {},
  auto_generate_alt_text: true,
  alt_text_style: "descriptive",
  suggestion_frequency: "balanced",
  confirm_before_apply: true,
  dismissed_suggestions: [],
  default_model: "sonnet",
  model_config: {
    chat: "sonnet",
    content_generation: "sonnet",
    seo_optimization: "haiku",
    content_analysis: "sonnet",
    image_analysis: "sonnet",
  },
  use_emojis: false,
  include_sources: false,
};

export function AIPreferencesPanel() {
  const { toast } = useToast();
  const [preferences, setPreferences] = useState<AIPreferences>(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  async function loadPreferences() {
    setLoading(true);
    try {
      const sessionId = localStorage.getItem("sessionId");
      if (!sessionId) throw new Error("Not logged in");

      const response = await fetch("http://localhost:8000/ai/preferences", {
        headers: { "X-Session-ID": sessionId },
      });

      if (!response.ok) throw new Error("Failed to load preferences");

      const data = await response.json();
      setPreferences(data);
    } catch (error) {
      toast({
        title: "Error loading preferences",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  async function savePreferences() {
    setSaving(true);
    try {
      const sessionId = localStorage.getItem("sessionId");
      if (!sessionId) throw new Error("Not logged in");

      const response = await fetch("http://localhost:8000/ai/preferences", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify(preferences),
      });

      if (!response.ok) throw new Error("Failed to save preferences");

      const data = await response.json();
      setPreferences(data);
      setHasChanges(false);

      toast({
        title: "Preferences saved",
        description: "Your AI preferences have been updated",
      });
    } catch (error) {
      toast({
        title: "Error saving preferences",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  function resetToDefaults() {
    setPreferences(DEFAULT_PREFERENCES);
    setHasChanges(true);
  }

  function updatePreference<K extends keyof AIPreferences>(
    key: K,
    value: AIPreferences[K]
  ) {
    setPreferences((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Loading preferences...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              AI Preferences
            </CardTitle>
            <CardDescription>
              Configure how Claude AI assists you across the platform
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={resetToDefaults}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset
            </Button>
            <Button
              size="sm"
              onClick={savePreferences}
              disabled={!hasChanges || saving}
            >
              <Save className="mr-2 h-4 w-4" />
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="writing">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="writing">Writing</TabsTrigger>
            <TabsTrigger value="seo">SEO</TabsTrigger>
            <TabsTrigger value="brand">Brand</TabsTrigger>
            <TabsTrigger value="images">Images</TabsTrigger>
            <TabsTrigger value="models">Models</TabsTrigger>
          </TabsList>

          <TabsContent value="writing" className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tone">Tone</Label>
                <Select
                  value={preferences.tone}
                  onValueChange={(value) => updatePreference("tone", value)}
                >
                  <SelectTrigger id="tone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="casual">Casual</SelectItem>
                    <SelectItem value="friendly">Friendly</SelectItem>
                    <SelectItem value="authoritative">Authoritative</SelectItem>
                    <SelectItem value="conversational">Conversational</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="audience">Audience</Label>
                <Select
                  value={preferences.audience}
                  onValueChange={(value) => updatePreference("audience", value)}
                >
                  <SelectTrigger id="audience">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="technical">Technical</SelectItem>
                    <SelectItem value="beginner">Beginner</SelectItem>
                    <SelectItem value="expert">Expert</SelectItem>
                    <SelectItem value="children">Children</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="writing-level">Writing Level</Label>
                <Select
                  value={preferences.writing_level}
                  onValueChange={(value) => updatePreference("writing_level", value)}
                >
                  <SelectTrigger id="writing-level">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="simple">Simple</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="advanced">Advanced</SelectItem>
                    <SelectItem value="academic">Academic</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="content-length">Content Length</Label>
                <Select
                  value={preferences.content_length}
                  onValueChange={(value) => updatePreference("content_length", value)}
                >
                  <SelectTrigger id="content-length">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="concise">Concise</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="detailed">Detailed</SelectItem>
                    <SelectItem value="comprehensive">Comprehensive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Use Emojis</Label>
                  <p className="text-sm text-muted-foreground">
                    Include emojis in AI-generated content
                  </p>
                </div>
                <Switch
                  checked={preferences.use_emojis}
                  onCheckedChange={(checked) =>
                    updatePreference("use_emojis", checked)
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Include Sources</Label>
                  <p className="text-sm text-muted-foreground">
                    Include source citations when applicable
                  </p>
                </div>
                <Switch
                  checked={preferences.include_sources}
                  onCheckedChange={(checked) =>
                    updatePreference("include_sources", checked)
                  }
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="seo" className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto-generate SEO</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically suggest SEO meta tags
                </p>
              </div>
              <Switch
                checked={preferences.auto_generate_seo}
                onCheckedChange={(checked) =>
                  updatePreference("auto_generate_seo", checked)
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="seo-style">SEO Style</Label>
              <Select
                value={preferences.seo_style}
                onValueChange={(value) => updatePreference("seo_style", value)}
              >
                <SelectTrigger id="seo-style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="clickbait">Clickbait</SelectItem>
                  <SelectItem value="informative">Informative</SelectItem>
                  <SelectItem value="balanced">Balanced</SelectItem>
                  <SelectItem value="conservative">Conservative</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Target Keyword Density: {preferences.target_keyword_density}%</Label>
              <Slider
                value={[preferences.target_keyword_density]}
                onValueChange={([value]) =>
                  updatePreference("target_keyword_density", value)
                }
                min={1}
                max={3}
                step={0.1}
              />
            </div>
          </TabsContent>

          <TabsContent value="brand" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="brand-voice">Brand Voice</Label>
              <Textarea
                id="brand-voice"
                placeholder="Describe your brand's voice and style..."
                value={preferences.brand_voice || ""}
                onChange={(e) =>
                  updatePreference("brand_voice", e.target.value || null)
                }
                rows={4}
              />
              <p className="text-sm text-muted-foreground">
                Custom instructions for maintaining your brand's unique voice
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="avoid-words">Avoid Words</Label>
              <Input
                id="avoid-words"
                placeholder="word1, word2, word3"
                value={preferences.avoid_words.join(", ")}
                onChange={(e) =>
                  updatePreference(
                    "avoid_words",
                    e.target.value.split(",").map((w) => w.trim()).filter(Boolean)
                  )
                }
              />
              <p className="text-sm text-muted-foreground">
                Comma-separated list of words to avoid
              </p>
            </div>
          </TabsContent>

          <TabsContent value="images" className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto-generate Alt Text</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically generate alt text for images
                </p>
              </div>
              <Switch
                checked={preferences.auto_generate_alt_text}
                onCheckedChange={(checked) =>
                  updatePreference("auto_generate_alt_text", checked)
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="alt-text-style">Alt Text Style</Label>
              <Select
                value={preferences.alt_text_style}
                onValueChange={(value) => updatePreference("alt_text_style", value)}
              >
                <SelectTrigger id="alt-text-style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="descriptive">Descriptive</SelectItem>
                  <SelectItem value="concise">Concise</SelectItem>
                  <SelectItem value="seo-focused">SEO-Focused</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </TabsContent>

          <TabsContent value="models" className="space-y-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="default-model">Default Model</Label>
                <Select
                  value={preferences.default_model}
                  onValueChange={(value) => updatePreference("default_model", value)}
                >
                  <SelectTrigger id="default-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sonnet">
                      Claude Sonnet 4.5 (Balanced)
                    </SelectItem>
                    <SelectItem value="opus">
                      Claude Opus 4 (Highest Quality)
                    </SelectItem>
                    <SelectItem value="haiku">
                      Claude Haiku 4 (Fastest)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="rounded-lg border p-4 space-y-3">
                <h4 className="font-medium">Per-Feature Models</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Chat:</span>
                    <Badge variant="outline">
                      {preferences.model_config.chat}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Content Gen:</span>
                    <Badge variant="outline">
                      {preferences.model_config.content_generation}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SEO:</span>
                    <Badge variant="outline">
                      {preferences.model_config.seo_optimization}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Analysis:</span>
                    <Badge variant="outline">
                      {preferences.model_config.content_analysis}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
