"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Sparkles, Loader2, Check } from "lucide-react";

interface ImageAltTextGeneratorProps {
  imageUrl: string;
  currentAltText?: string;
  onAltTextChange: (altText: string) => void;
  context?: string;
}

export function ImageAltTextGenerator({
  imageUrl,
  currentAltText = "",
  onAltTextChange,
  context,
}: ImageAltTextGeneratorProps) {
  const { toast } = useToast();
  const [altText, setAltText] = useState(currentAltText);
  const [generating, setGenerating] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  async function generateAltText() {
    setGenerating(true);
    setSuggestions([]);

    try {
      const sessionId = localStorage.getItem("sessionId");
      if (!sessionId) throw new Error("Not logged in");

      const response = await fetch("http://localhost:8000/ai/generate-alt-text", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          image_url: imageUrl,
          context: context || "",
        }),
      });

      if (!response.ok) throw new Error("Failed to generate alt text");

      const data = await response.json();
      setSuggestions(data.suggestions || []);

      // Auto-apply the first suggestion
      if (data.alt_text) {
        setAltText(data.alt_text);
        onAltTextChange(data.alt_text);
      }

      toast({
        title: "Alt text generated",
        description: "AI-generated alt text has been applied",
      });
    } catch (error) {
      toast({
        title: "Generation failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setGenerating(false);
    }
  }

  function applySuggestion(suggestion: string) {
    setAltText(suggestion);
    onAltTextChange(suggestion);
    toast({
      title: "Alt text applied",
      description: "Selected alt text has been applied",
    });
  }

  function handleManualChange(value: string) {
    setAltText(value);
    onAltTextChange(value);
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="alt-text">Alt Text</Label>
          <Button
            variant="outline"
            size="sm"
            onClick={generateAltText}
            disabled={generating}
            className="gap-2"
          >
            {generating ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-3 w-3" />
                Generate with AI
              </>
            )}
          </Button>
        </div>

        <Textarea
          id="alt-text"
          value={altText}
          onChange={(e) => handleManualChange(e.target.value)}
          placeholder="Describe this image for accessibility..."
          rows={3}
          maxLength={250}
        />

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {altText.length > 0
              ? `${altText.length}/250 characters`
              : "Alt text helps screen readers and SEO"}
          </span>
          {altText.length > 125 && (
            <span className="text-amber-600">
              Consider keeping alt text under 125 characters
            </span>
          )}
        </div>
      </div>

      {/* AI Suggestions */}
      {suggestions.length > 0 && (
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">AI Suggestions</Label>
          <div className="space-y-1">
            {suggestions.map((suggestion, index) => (
              <div
                key={index}
                className={`p-2 text-sm border rounded-md cursor-pointer transition-colors ${
                  altText === suggestion
                    ? "bg-primary/10 border-primary"
                    : "hover:bg-accent"
                }`}
                onClick={() => applySuggestion(suggestion)}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="flex-1">{suggestion}</p>
                  {altText === suggestion && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
