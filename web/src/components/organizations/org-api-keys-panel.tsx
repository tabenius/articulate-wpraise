"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { Key, Copy, Trash2, Download, ExternalLink } from "lucide-react";
import { ApiKeysSkeleton } from "@/components/skeletons/api-keys-skeleton";

interface ApiKey {
  id: number;
  key_prefix: string;
  description: string | null;
  expires_at: string;
  used_at: string | null;
  is_active: boolean;
  created_at: string;
  created_by: string;
}

interface OrgApiKeysPanelProps {
  organizationId: number;
}

export function OrgApiKeysPanel({ organizationId }: OrgApiKeysPanelProps) {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newKeyData, setNewKeyData] = useState<{ key: string } | null>(null);
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadKeys();
  }, [organizationId]);

  async function loadKeys() {
    try {
      setIsLoading(true);
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(
        `http://localhost:8000/organizations/${organizationId}/api-keys`,
        { headers: { "X-Session-ID": sessionId || "" } }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setKeys(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load API keys:", error);
      toast({
        title: "Failed to load API keys",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function createKey() {
    try {
      setIsCreating(true);
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(
        `http://localhost:8000/organizations/${organizationId}/api-keys`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-ID": sessionId || "",
          },
          body: JSON.stringify({
            description: description.trim() || null,
            expiry_days: 7,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setNewKeyData({ key: data.key });
      loadKeys(); // Reload the list
      setDescription("");

      toast({
        title: "API Key Created",
        description: "Copy the key now - it won't be shown again!",
      });
    } catch (error) {
      toast({
        title: "Failed to create API key",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  }

  async function revokeKey(keyId: number) {
    if (!confirm("Are you sure you want to revoke this key? This action cannot be undone.")) {
      return;
    }

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(
        `http://localhost:8000/organizations/${organizationId}/api-keys/${keyId}`,
        {
          method: "DELETE",
          headers: { "X-Session-ID": sessionId || "" },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      loadKeys();
      toast({ title: "API Key Revoked" });
    } catch (error) {
      toast({
        title: "Failed to revoke key",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied to clipboard" });
  }

  function downloadPlugin() {
    // Trigger download of plugin ZIP
    window.open("/downloads/wp-ai-connector.zip", "_blank");
  }

  function getKeyStatus(key: ApiKey) {
    if (key.used_at) {
      return { label: "Used", className: "text-green-600" };
    }
    if (!key.is_active) {
      return { label: "Revoked", className: "text-gray-500" };
    }
    if (new Date(key.expires_at) < new Date()) {
      return { label: "Expired", className: "text-red-600" };
    }
    return { label: "Active", className: "text-blue-600" };
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Organization API Keys</h3>
          <p className="text-sm text-muted-foreground">
            Create single-use registration keys for remote WordPress sites
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={downloadPlugin}>
            <Download className="mr-2 h-4 w-4" />
            Download Plugin
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Key className="mr-2 h-4 w-4" />
            Create API Key
          </Button>
        </div>
      </div>

      {/* API Key Creation Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={(open) => {
        setIsCreateDialogOpen(open);
        if (!open) {
          setNewKeyData(null);
          setDescription("");
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Registration API Key</DialogTitle>
            <DialogDescription>
              Single-use key for registering a remote WordPress site
            </DialogDescription>
          </DialogHeader>

          {newKeyData ? (
            <div className="space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-md">
                <p className="text-sm font-medium text-yellow-800 mb-2">
                  ⚠️ Save this key now! It won't be displayed again.
                </p>
                <div className="flex gap-2">
                  <Input
                    value={newKeyData.key}
                    readOnly
                    className="font-mono text-xs"
                  />
                  <Button size="sm" onClick={() => copyToClipboard(newKeyData.key)}>
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 p-3 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>Next steps:</strong>
                </p>
                <ol className="text-sm text-blue-800 mt-2 ml-4 list-decimal space-y-1">
                  <li>Copy the API key above</li>
                  <li>Download the WordPress plugin</li>
                  <li>Install the plugin on your WordPress site</li>
                  <li>Paste the API key in the plugin settings</li>
                </ol>
              </div>

              <DialogFooter>
                <Button
                  onClick={() => {
                    setIsCreateDialogOpen(false);
                    setNewKeyData(null);
                  }}
                >
                  Done
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <Label htmlFor="description">Description (optional)</Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., Production site registration"
                  maxLength={500}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Help identify what this key is for
                </p>
              </div>

              <div className="bg-muted p-3 rounded-md text-sm space-y-1">
                <p className="font-medium">Key Details:</p>
                <ul className="list-disc ml-4 text-muted-foreground">
                  <li>Valid for 7 days</li>
                  <li>Single-use (expires after first use)</li>
                  <li>Can be revoked at any time</li>
                </ul>
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button onClick={createKey} disabled={isCreating}>
                  {isCreating ? "Creating..." : "Create Key"}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Keys List */}
      {isLoading ? (
        <ApiKeysSkeleton />
      ) : keys.length === 0 ? (
        <div className="text-center py-12 border rounded-lg border-dashed">
          <Key className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-4">
            No API keys created yet
          </p>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            Create Your First API Key
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Created By</TableHead>
                <TableHead className="w-[100px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((key) => {
                const status = getKeyStatus(key);
                return (
                  <TableRow key={key.id}>
                    <TableCell className="font-mono text-sm">
                      {key.key_prefix}...
                    </TableCell>
                    <TableCell>{key.description || <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell>
                      <span className={`font-medium ${status.className}`}>
                        {status.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      {new Date(key.expires_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-sm">{key.created_by}</TableCell>
                    <TableCell>
                      {key.is_active && !key.used_at && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => revokeKey(key.id)}
                          title="Revoke key"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Help Section */}
      <div className="bg-muted/50 p-4 rounded-lg border">
        <h4 className="font-semibold mb-2 flex items-center gap-2">
          <ExternalLink className="h-4 w-4" />
          How to Register a WordPress Site
        </h4>
        <ol className="text-sm text-muted-foreground ml-6 list-decimal space-y-1">
          <li>Create an API key above</li>
          <li>Download the WP-AI Connector plugin</li>
          <li>Install and activate the plugin on your WordPress site</li>
          <li>Go to Settings → WP-AI Connector in WordPress admin</li>
          <li>Paste your API key and complete the registration</li>
        </ol>
        <p className="text-sm text-muted-foreground mt-3">
          Once registered, the site will appear in your organization's connections list
          and can be managed through the WP-AI platform.
        </p>
      </div>
    </div>
  );
}
