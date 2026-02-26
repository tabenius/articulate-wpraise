"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Key, Eye, EyeOff, Check } from "lucide-react";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (open) {
      const stored = localStorage.getItem("articulate-api-key") || "";
      setApiKey(stored);
      setSaved(false);
    }
  }, [open]);

  const handleSave = () => {
    if (apiKey.trim()) {
      localStorage.setItem("articulate-api-key", apiKey.trim());
    } else {
      localStorage.removeItem("articulate-api-key");
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClear = () => {
    setApiKey("");
    localStorage.removeItem("articulate-api-key");
    setSaved(false);
  };

  const hasServerKey = true; // We show this info regardless

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Configure your Articulate preferences.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* API Key Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-muted-foreground" />
              <h3 className="text-sm font-medium">Anthropic API Key</h3>
            </div>

            <p className="text-xs text-muted-foreground">
              Provide your own API key, or leave blank to use the server&apos;s
              default key (if configured).
            </p>

            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setSaved(false);
                }}
                placeholder="sk-ant-..."
                className="w-full px-3 py-2 pr-10 border rounded-md text-sm bg-background font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>

            <div className="flex gap-2">
              <Button size="sm" onClick={handleSave} disabled={saved}>
                {saved ? (
                  <>
                    <Check className="h-3.5 w-3.5 mr-1" />
                    Saved
                  </>
                ) : (
                  "Save Key"
                )}
              </Button>
              {apiKey && (
                <Button size="sm" variant="outline" onClick={handleClear}>
                  Clear
                </Button>
              )}
            </div>

            <p className="text-[11px] text-muted-foreground">
              Your key is stored locally in your browser and sent securely via
              request headers. It is never logged or stored on the server.
            </p>
          </div>

          {/* Info Section */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium mb-2">About</h3>
            <div className="text-xs text-muted-foreground space-y-1">
              <p>Articulate uses Claude Sonnet 4.5 for AI-assisted content editing.</p>
              <p>WordPress content is managed via WPGraphQL and the MCP protocol.</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
