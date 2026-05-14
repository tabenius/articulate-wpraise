"use client";

import { useState } from "react";
import { useConnections } from "@/contexts/connection-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { Plus, Trash2, Check, Server, Copy, RefreshCw } from "lucide-react";
import { RemoteSetupDialog } from "@/components/connections/remote-setup-dialog";

type ConnectionFormData = {
  name: string;
  wp_url: string;
  wp_graphql_endpoint: string;
  wp_user: string;
  wp_app_password: string;
};

function isValidHttpUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function validateConnectionFormData(data: ConnectionFormData): string[] {
  const errors: string[] = [];
  if (!data.name.trim()) errors.push("Connection name is required.");
  if (!data.wp_user.trim()) errors.push("WordPress username is required.");
  if (!data.wp_app_password.trim()) errors.push("Application password is required.");
  if (data.wp_app_password.trim().length < 8) {
    errors.push("Application password appears too short.");
  }
  if (!isValidHttpUrl(data.wp_url.trim())) {
    errors.push("WordPress URL must be a valid http/https URL.");
  }
  if (!isValidHttpUrl(data.wp_graphql_endpoint.trim())) {
    errors.push("GraphQL endpoint must be a valid http/https URL.");
  } else if (!data.wp_graphql_endpoint.includes("/graphql")) {
    errors.push("GraphQL endpoint should include '/graphql'.");
  }
  return errors;
}

export default function ConnectionsPage() {
  const { connections, activeConnection, addConnection, deleteConnection, activateConnection, isLoading } = useConnections();
  const { toast } = useToast();

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isRemoteSetupOpen, setIsRemoteSetupOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    wp_url: "",
    wp_graphql_endpoint: "",
    wp_user: "",
    wp_app_password: "",
  });
  const [isErrorModalOpen, setIsErrorModalOpen] = useState(false);
  const [errorModalData, setErrorModalData] = useState<any>(null);
  const [errorModalMessage, setErrorModalMessage] = useState("");
  const [formErrors, setFormErrors] = useState<string[]>([]);

  async function handleAddConnection(e: React.FormEvent) {
    e.preventDefault();
    const validationErrors = validateConnectionFormData(formData);
    if (validationErrors.length > 0) {
      setFormErrors(validationErrors);
      toast({
        title: "Invalid connection form data",
        description: validationErrors.join(" "),
        variant: "destructive",
      });
      return;
    }
    setFormErrors([]);

    try {
      await addConnection({
        name: formData.name.trim(),
        wp_url: formData.wp_url.trim(),
        wp_graphql_endpoint: formData.wp_graphql_endpoint.trim(),
        wp_user: formData.wp_user.trim(),
        wp_app_password: formData.wp_app_password.trim(),
      });
      toast({
        title: "Connection added",
        description: `Successfully added connection: ${formData.name}`,
      });
      setIsAddDialogOpen(false);
      setFormData({
        name: "",
        wp_url: "",
        wp_graphql_endpoint: "",
        wp_user: "",
        wp_app_password: "",
      });
    } catch (error) {
      toast({
        title: "Failed to add connection",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleDeleteConnection(id: number, name: string) {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    try {
      await deleteConnection(id);
      toast({
        title: "Connection deleted",
        description: `Successfully deleted connection: ${name}`,
      });
    } catch (error) {
      toast({
        title: "Failed to delete connection",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleActivateConnection(id: number, name: string) {
    try {
      await activateConnection(id);
      toast({
        title: "Connection activated",
        description: `Now using: ${name}`,
      });
    } catch (error) {
      toast({
        title: "Failed to activate connection",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleRegenerateMcpKey(id: number, name: string) {
    if (!confirm(`Regenerate MCP API key for "${name}"? Existing Claude Desktop connections using this key will stop working.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/connections/${id}/regenerate-mcp-key`, {
        method: "POST",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to regenerate key");
      }

      toast({
        title: "API key regenerated",
        description: `New MCP key generated for ${name}`,
      });
      // Refresh to show new key
      window.location.reload();
    } catch (error) {
      toast({
        title: "Failed to regenerate key",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function getMcpUrl(apiKey: string | null | undefined): string {
    if (!apiKey) return "";
    const host = typeof window !== "undefined" ? window.location.origin : "";
    return `${host}/api/mcp/c/${apiKey}`;
  }

  async function copyToClipboard(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast({ title: "Copied", description: `${label} copied to clipboard` });
    } catch {
      toast({ title: "Copy failed", variant: "destructive" });
    }
  }

  async function handleInstallLearnpress(id: number, name: string) {
    if (!confirm(`Install LearnPress on "${name}"? This may require admin permissions.`)) {
      return;
    }
    const sessionId = localStorage.getItem("session_id");
    if (!sessionId) {
      toast({ title: "Not authenticated", description: "Please sign in", variant: "destructive" });
      return;
    }
    try {
      const response = await fetch(`/api/connections/${id}/learnpress/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plugin_slug: "learnpress" }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const human = data?.error_info?.message || data?.error || data?.details || "Install failed";
        // Open modal showing human message and full error details for copy
        setErrorModalMessage(human);
        setErrorModalData(data);
        setIsErrorModalOpen(true);
        return;
      }

      // success
      toast({ title: "Plugin installed", description: `LearnPress installed on ${name}` });
    } catch (error) {
      const desc = error instanceof Error ? error.message : "An error occurred";
      setErrorModalMessage(desc);
      setErrorModalData({ message: desc });
      setIsErrorModalOpen(true);
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading connections...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">WordPress Connections</h1>
          <p className="text-gray-600">
            Manage your WordPress site connections
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setIsRemoteSetupOpen(true)}
          >
            <Server className="mr-2 h-4 w-4" />
            Setup Remote
          </Button>

          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Connection
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add WordPress Connection</DialogTitle>
              <DialogDescription>
                Connect to a WordPress site using WPGraphQL
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddConnection} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Connection Name</Label>
                <Input
                  id="name"
                  placeholder="My Blog"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wp_url">WordPress URL</Label>
                <Input
                  id="wp_url"
                  type="url"
                  placeholder="https://example.com"
                  value={formData.wp_url}
                  onChange={(e) => setFormData({ ...formData, wp_url: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wp_graphql_endpoint">GraphQL Endpoint</Label>
                <Input
                  id="wp_graphql_endpoint"
                  type="url"
                  placeholder="https://example.com/graphql"
                  value={formData.wp_graphql_endpoint}
                  onChange={(e) => setFormData({ ...formData, wp_graphql_endpoint: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wp_user">WordPress Username</Label>
                <Input
                  id="wp_user"
                  placeholder="admin"
                  value={formData.wp_user}
                  onChange={(e) => setFormData({ ...formData, wp_user: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="wp_app_password">Application Password</Label>
                <Input
                  id="wp_app_password"
                  type="password"
                  placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                  value={formData.wp_app_password}
                  onChange={(e) => setFormData({ ...formData, wp_app_password: e.target.value })}
                  required
                />
                <p className="text-xs text-gray-500">
                  Generate an application password in WordPress Users → Profile
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsAddDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit">Add Connection</Button>
              </div>
              {formErrors.length > 0 && (
                <div className="text-sm text-red-600 space-y-1">
                  {formErrors.map((err) => (
                    <p key={err}>{err}</p>
                  ))}
                </div>
              )}
            </form>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {connections.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No connections yet</CardTitle>
            <CardDescription>
              Add your first WordPress connection to get started
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connections.map((connection) => (
            <Card
              key={connection.id}
              className={connection.is_active ? "border-blue-500 border-2" : ""}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {connection.name}
                      {connection.is_active && (
                        <span className="flex items-center text-sm font-normal text-blue-600">
                          <Check className="mr-1 h-3 w-3" />
                          Active
                        </span>
                      )}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {connection.wp_url}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <p>
                    <span className="font-medium">User:</span> {connection.wp_user}
                  </p>
                  <p>
                    <span className="font-medium">Created:</span>{" "}
                    {new Date(connection.created_at).toLocaleDateString()}
                  </p>
                </div>

                {connection.mcp_api_key && (
                  <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-2">
                    <p className="text-xs font-medium text-gray-500">MCP URL (for Claude Desktop)</p>
                    <div className="flex items-center gap-1">
                      <code className="text-xs font-mono break-all flex-1 text-gray-700 dark:text-gray-300">
                        {getMcpUrl(connection.mcp_api_key)}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 shrink-0"
                        onClick={() => copyToClipboard(getMcpUrl(connection.mcp_api_key), "MCP URL")}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs text-gray-500"
                      onClick={() => handleRegenerateMcpKey(connection.id, connection.name)}
                    >
                      <RefreshCw className="mr-1 h-3 w-3" />
                      Regenerate Key
                    </Button>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  {!connection.is_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActivateConnection(connection.id, connection.name)}
                      className="flex-1"
                    >
                      Activate
                    </Button>
                  )}
                  <Button size="sm" onClick={() => handleInstallLearnpress(connection.id, connection.name)}>
                    Install LearnPress
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteConnection(connection.id, connection.name)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={isErrorModalOpen} onOpenChange={setIsErrorModalOpen}>
    <DialogContent className="max-w-2xl">
      <DialogHeader>
        <DialogTitle>Install error</DialogTitle>
        <DialogDescription>{errorModalMessage}</DialogDescription>
      </DialogHeader>
      <pre className="whitespace-pre-wrap bg-gray-100 p-3 rounded text-sm overflow-auto max-h-64">{errorModalData ? JSON.stringify(errorModalData, null, 2) : ""}</pre>
      <div className="mt-4 flex justify-end gap-2">
        <Button onClick={async () => {
          try {
            await navigator.clipboard.writeText(JSON.stringify(errorModalData, null, 2));
            toast({ title: "Error details copied", description: "Full error info copied to clipboard" });
          } catch (e) {
            toast({ title: "Copy failed", description: "Could not copy error details", variant: "destructive" });
          }
        }}>Copy details</Button>
        <Button variant="outline" onClick={() => setIsErrorModalOpen(false)}>Close</Button>
      </div>
    </DialogContent>
  </Dialog>

  <RemoteSetupDialog
        open={isRemoteSetupOpen}
        onOpenChange={setIsRemoteSetupOpen}
        onSuccess={(connection) => {
          toast({
            title: "Remote WordPress setup complete",
            description: `Successfully configured ${connection.name}`,
          });
          // Refresh connections list
          window.location.reload();
        }}
      />
    </div>
  );
}
