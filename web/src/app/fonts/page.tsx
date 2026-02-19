"use client";

import { useState, useEffect } from "react";
import { FontUpload } from "@/components/fonts/font-upload";
import { Button } from "@/components/ui/button";
import { Trash2, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Font {
  id: string;
  family: string;
  weight: string;
  style: string;
  url: string;
  format: string;
  css: string;
  uploaded_at?: string;
}

export default function FontsPage() {
  const [fonts, setFonts] = useState<Font[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { toast } = useToast();

  const loadFonts = async () => {
    try {
      setRefreshing(true);
      const response = await fetch("/api/fonts");
      const data = await response.json();

      if (Array.isArray(data)) {
        setFonts(data);
      } else if (data.error) {
        toast({
          title: "Error loading fonts",
          description: data.error,
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error loading fonts",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadFonts();
  }, []);

  const handleUploadSuccess = () => {
    loadFonts();
  };

  const handleDelete = async (fontId: string) => {
    if (!confirm("Are you sure you want to delete this font?")) {
      return;
    }

    try {
      const response = await fetch(`/api/fonts/${fontId}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (data.error) {
        toast({
          title: "Error deleting font",
          description: data.error,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Font deleted",
          description: "Font has been removed successfully",
        });
        loadFonts();
      }
    } catch (error) {
      toast({
        title: "Error deleting font",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Font Management</h1>
        <p className="text-gray-600">
          Upload and manage custom fonts for your WordPress site
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <FontUpload onUploadSuccess={handleUploadSuccess} />
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Registered Fonts</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={loadFonts}
          disabled={refreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading fonts...</p>
        </div>
      ) : fonts.length === 0 ? (
        <div className="text-center py-12 border rounded-lg bg-muted">
          <p className="text-gray-500">No fonts uploaded yet</p>
          <p className="text-sm text-gray-400 mt-2">
            Upload your first font using the form above
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {fonts.map((font) => (
            <div
              key={font.id}
              className="border rounded-lg p-4 bg-card hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg truncate">{font.family}</h3>
                  <p className="text-sm text-gray-500">
                    Weight: {font.weight} · Style: {font.style}
                  </p>
                  <p className="text-xs text-gray-400 mt-1 uppercase">
                    {font.format}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(font.id)}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>

              <div
                className="border rounded p-3 bg-background"
                style={{
                  fontFamily: `'${font.family}', sans-serif`,
                  fontWeight: parseInt(font.weight),
                  fontStyle: font.style,
                }}
              >
                <p className="text-xl leading-relaxed">
                  The quick brown fox jumps over the lazy dog
                </p>
              </div>

              <details className="mt-3">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                  View CSS
                </summary>
                <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-x-auto">
                  {font.css}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
