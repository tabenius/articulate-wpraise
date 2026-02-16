"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Palette, Type, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";

// Color Palettes
const colorPalettes = [
  {
    name: "Ocean Breeze",
    colors: ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087"],
    description: "Professional and trustworthy",
  },
  {
    name: "Sunset Glow",
    colors: ["#f95d6a", "#ff7c43", "#ffa600", "#d45087", "#a05195"],
    description: "Warm and energetic",
  },
  {
    name: "Forest Calm",
    colors: ["#2d6a4f", "#40916c", "#52b788", "#74c69d", "#95d5b2"],
    description: "Natural and peaceful",
  },
  {
    name: "Modern Minimal",
    colors: ["#1a1a1a", "#333333", "#666666", "#999999", "#cccccc"],
    description: "Clean and sophisticated",
  },
  {
    name: "Vibrant Pop",
    colors: ["#ff006e", "#fb5607", "#ffbe0b", "#8338ec", "#3a86ff"],
    description: "Bold and playful",
  },
  {
    name: "Corporate Blue",
    colors: ["#023047", "#126782", "#219ebc", "#8ecae6", "#ffffff"],
    description: "Professional and reliable",
  },
];

// Typography Pairs
const typographyPairs = [
  {
    name: "Classic Serif",
    heading: { font: "Playfair Display", weight: "700", example: "Elegant Headlines" },
    body: { font: "Source Sans Pro", weight: "400", example: "Clean, readable body text that flows naturally" },
    use: "Editorial, luxury brands, traditional content",
  },
  {
    name: "Modern Sans",
    heading: { font: "Inter", weight: "800", example: "Bold Modern Headers" },
    body: { font: "Inter", weight: "400", example: "Consistent, clean typography throughout" },
    use: "Tech, startups, contemporary design",
  },
  {
    name: "Geometric Pair",
    heading: { font: "Montserrat", weight: "700", example: "Strong Geometric Titles" },
    body: { font: "Open Sans", weight: "400", example: "Friendly and approachable body copy" },
    use: "Marketing, creative agencies, portfolios",
  },
  {
    name: "Editorial Style",
    heading: { font: "Merriweather", weight: "900", example: "Authoritative Headlines" },
    body: { font: "Lato", weight: "400", example: "Professional content that's easy to read" },
    use: "Blogs, news, long-form content",
  },
  {
    name: "Tech Forward",
    heading: { font: "Space Grotesk", weight: "700", example: "Futuristic Headers" },
    body: { font: "IBM Plex Sans", weight: "400", example: "Technical yet readable body text" },
    use: "SaaS, tech companies, documentation",
  },
];

// Button Themes
const buttonThemes = [
  {
    name: "Solid Primary",
    preview: { bg: "#3b82f6", text: "#ffffff", border: "none", radius: "0.375rem" },
    css: "bg-blue-500 text-white hover:bg-blue-600 rounded-md px-4 py-2 font-medium",
  },
  {
    name: "Outline Modern",
    preview: { bg: "transparent", text: "#3b82f6", border: "2px solid #3b82f6", radius: "0.5rem" },
    css: "border-2 border-blue-500 text-blue-500 hover:bg-blue-50 rounded-lg px-4 py-2",
  },
  {
    name: "Soft Shadow",
    preview: { bg: "#6366f1", text: "#ffffff", border: "none", radius: "0.75rem", shadow: "0 4px 6px rgba(99, 102, 241, 0.3)" },
    css: "bg-indigo-500 text-white rounded-xl px-6 py-3 shadow-lg hover:shadow-xl",
  },
  {
    name: "Gradient Bold",
    preview: { bg: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", text: "#ffffff", border: "none", radius: "0.5rem" },
    css: "bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg px-5 py-2.5 font-semibold",
  },
  {
    name: "Minimal Ghost",
    preview: { bg: "transparent", text: "#374151", border: "none", radius: "0.25rem" },
    css: "text-gray-700 hover:bg-gray-100 rounded px-3 py-2 transition-colors",
  },
];

// Heading Themes
const headingThemes = [
  {
    name: "Bold Impact",
    h1: "font-black text-5xl tracking-tight",
    h2: "font-bold text-4xl",
    h3: "font-semibold text-2xl",
    preview: "Maximum Impact",
  },
  {
    name: "Editorial Classic",
    h1: "font-serif font-bold text-5xl leading-tight",
    h2: "font-serif font-semibold text-3xl",
    h3: "font-serif font-medium text-xl",
    preview: "Timeless Elegance",
  },
  {
    name: "Modern Minimal",
    h1: "font-light text-4xl tracking-wide",
    h2: "font-normal text-3xl",
    h3: "font-medium text-xl",
    preview: "Clean & Simple",
  },
  {
    name: "Tech Sans",
    h1: "font-extrabold text-5xl tracking-tight uppercase",
    h2: "font-bold text-3xl uppercase",
    h3: "font-semibold text-xl",
    preview: "STRONG PRESENCE",
  },
];

// Body Text Themes
const bodyTextThemes = [
  {
    name: "Standard Readable",
    css: "text-base leading-7 text-gray-700",
    preview: "Easy to read for long-form content with comfortable line height and spacing.",
  },
  {
    name: "Compact Dense",
    css: "text-sm leading-6 text-gray-800",
    preview: "Information-dense layout perfect for dashboards and data-heavy pages.",
  },
  {
    name: "Large Accessible",
    css: "text-lg leading-8 text-gray-600",
    preview: "Highly accessible with larger text size ideal for broader audiences.",
  },
  {
    name: "Editorial Serif",
    css: "font-serif text-base leading-8 text-gray-900",
    preview: "Traditional reading experience with classic serif fonts and generous spacing.",
  },
];

export function DesignSystemPanel() {
  const [open, setOpen] = useState(false);
  const { toast } = useToast();

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied to clipboard",
      description: `${label} CSS classes copied`,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Sparkles className="h-4 w-4 mr-2" />
          Design System
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Design System Tools
          </DialogTitle>
          <DialogDescription>
            Professional color palettes, typography pairs, and component themes
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[calc(90vh-8rem)]">
          <div className="space-y-8 pr-4">
            {/* Color Palettes */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Palette className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Color Palettes</h3>
              </div>
              <div className="grid gap-4">
                {colorPalettes.map((palette) => (
                  <div
                    key={palette.name}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => {
                      copyToClipboard(palette.colors.join(", "), palette.name);
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="font-medium">{palette.name}</h4>
                        <p className="text-xs text-muted-foreground">{palette.description}</p>
                      </div>
                      <Badge variant="secondary">Click to copy</Badge>
                    </div>
                    <div className="flex gap-1">
                      {palette.colors.map((color, idx) => (
                        <div
                          key={idx}
                          className="flex-1 h-16 rounded-md shadow-sm"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <Separator />

            {/* Typography Pairs */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Type className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Typography Pairs</h3>
              </div>
              <div className="grid gap-4">
                {typographyPairs.map((pair) => (
                  <div
                    key={pair.name}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium">{pair.name}</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          copyToClipboard(
                            `Heading: ${pair.heading.font} ${pair.heading.weight}\nBody: ${pair.body.font} ${pair.body.weight}`,
                            pair.name
                          );
                        }}
                      >
                        Copy
                      </Button>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <div className="text-xs text-muted-foreground mb-1">
                          Heading: {pair.heading.font} {pair.heading.weight}
                        </div>
                        <div
                          className="text-2xl"
                          style={{
                            fontFamily: pair.heading.font,
                            fontWeight: pair.heading.weight,
                          }}
                        >
                          {pair.heading.example}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground mb-1">
                          Body: {pair.body.font} {pair.body.weight}
                        </div>
                        <div
                          className="text-sm"
                          style={{
                            fontFamily: pair.body.font,
                            fontWeight: pair.body.weight,
                          }}
                        >
                          {pair.body.example}
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground italic">
                        Best for: {pair.use}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <Separator />

            {/* Button Themes */}
            <section>
              <h3 className="text-lg font-semibold mb-4">Button Themes</h3>
              <div className="grid grid-cols-2 gap-4">
                {buttonThemes.map((theme) => (
                  <div
                    key={theme.name}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <h4 className="font-medium text-sm mb-3">{theme.name}</h4>
                    <div className="mb-3 flex justify-center">
                      <div
                        className="px-4 py-2 font-medium cursor-pointer transition-all"
                        style={{
                          background: theme.preview.bg,
                          color: theme.preview.text,
                          border: theme.preview.border,
                          borderRadius: theme.preview.radius,
                          boxShadow: theme.preview.shadow,
                        }}
                      >
                        Button
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full"
                      onClick={() => copyToClipboard(theme.css, theme.name)}
                    >
                      Copy CSS
                    </Button>
                  </div>
                ))}
              </div>
            </section>

            <Separator />

            {/* Heading Themes */}
            <section>
              <h3 className="text-lg font-semibold mb-4">Heading Themes</h3>
              <div className="grid gap-4">
                {headingThemes.map((theme) => (
                  <div
                    key={theme.name}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">{theme.name}</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          copyToClipboard(
                            `H1: ${theme.h1}\nH2: ${theme.h2}\nH3: ${theme.h3}`,
                            theme.name
                          )
                        }
                      >
                        Copy
                      </Button>
                    </div>
                    <div className={theme.h1 + " mb-2"}>{theme.preview}</div>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>H1: {theme.h1}</div>
                      <div>H2: {theme.h2}</div>
                      <div>H3: {theme.h3}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <Separator />

            {/* Body Text Themes */}
            <section>
              <h3 className="text-lg font-semibold mb-4">Body Text Themes</h3>
              <div className="grid gap-4">
                {bodyTextThemes.map((theme) => (
                  <div
                    key={theme.name}
                    className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">{theme.name}</h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(theme.css, theme.name)}
                      >
                        Copy CSS
                      </Button>
                    </div>
                    <div className={theme.css + " mb-2"}>{theme.preview}</div>
                    <div className="text-xs text-muted-foreground">{theme.css}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
