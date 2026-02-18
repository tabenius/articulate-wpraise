"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, AlertCircle, Server, Loader2 } from "lucide-react";

interface RemoteSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (connectionInfo: any) => void;
}

export function RemoteSetupDialog({ open, onOpenChange, onSuccess }: RemoteSetupDialogProps) {
  const [authMethod, setAuthMethod] = useState<"key" | "password">("key");
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [output, setOutput] = useState("");
  const [connectionInfo, setConnectionInfo] = useState<any>(null);

  const [formData, setFormData] = useState({
    host: "",
    user: "",
    port: "22",
    ssh_key: "",
    ssh_password: "",
    auto_create: true,
  });

  const resetForm = () => {
    setFormData({
      host: "",
      user: "",
      port: "22",
      ssh_key: "",
      ssh_password: "",
      auto_create: true,
    });
    setStatus("idle");
    setProgress(0);
    setErrorMessage("");
    setOutput("");
    setConnectionInfo(null);
  };

  const handleClose = () => {
    if (status !== "running") {
      resetForm();
      onOpenChange(false);
    }
  };

  async function handleSetup(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    setStatus("running");
    setProgress(10);
    setErrorMessage("");
    setOutput("");

    try {
      // Get session ID from localStorage
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) {
        throw new Error("Not authenticated");
      }

      setProgress(20);

      // Prepare request data
      const requestData: any = {
        host: formData.host,
        user: formData.user,
        port: parseInt(formData.port),
        auto_create: formData.auto_create,
      };

      if (authMethod === "key") {
        requestData.ssh_key = formData.ssh_key;
      } else {
        requestData.ssh_password = formData.ssh_password;
      }

      setProgress(30);

      // Call MCP server endpoint
      const response = await fetch("http://localhost:8000/connections/setup-remote", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify(requestData),
      });

      setProgress(90);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Setup failed");
      }

      const result = await response.json();
      setProgress(100);
      setStatus("success");
      setConnectionInfo(result.connection_info);
      setOutput(result.output || "");

      if (onSuccess && result.connection) {
        onSuccess(result.connection);
      }
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Setup Remote WordPress
          </DialogTitle>
          <DialogDescription>
            Automatically configure a remote WordPress instance via SSH
          </DialogDescription>
        </DialogHeader>

        {status === "idle" && (
          <form onSubmit={handleSetup} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="host">Host *</Label>
                <Input
                  id="host"
                  placeholder="example.com"
                  value={formData.host}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="user">SSH User *</Label>
                <Input
                  id="user"
                  placeholder="ubuntu"
                  value={formData.user}
                  onChange={(e) => setFormData({ ...formData, user: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="port">SSH Port</Label>
              <Input
                id="port"
                type="number"
                placeholder="22"
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: e.target.value })}
              />
            </div>

            <Tabs value={authMethod} onValueChange={(v) => setAuthMethod(v as "key" | "password")}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="key">SSH Key (Recommended)</TabsTrigger>
                <TabsTrigger value="password">Password</TabsTrigger>
              </TabsList>

              <TabsContent value="key" className="space-y-2">
                <Label htmlFor="ssh_key">SSH Private Key *</Label>
                <Textarea
                  id="ssh_key"
                  placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
                  value={formData.ssh_key}
                  onChange={(e) => setFormData({ ...formData, ssh_key: e.target.value })}
                  rows={6}
                  className="font-mono text-xs"
                  required={authMethod === "key"}
                />
                <p className="text-xs text-gray-500">
                  Paste your SSH private key content (e.g., ~/.ssh/id_rsa)
                </p>
              </TabsContent>

              <TabsContent value="password" className="space-y-2">
                <Label htmlFor="ssh_password">SSH Password *</Label>
                <Input
                  id="ssh_password"
                  type="password"
                  placeholder="Your SSH password"
                  value={formData.ssh_password}
                  onChange={(e) => setFormData({ ...formData, ssh_password: e.target.value })}
                  required={authMethod === "password"}
                />
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    Password authentication is less secure. SSH keys are recommended.
                  </AlertDescription>
                </Alert>
              </TabsContent>
            </Tabs>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="auto_create"
                checked={formData.auto_create}
                onChange={(e) => setFormData({ ...formData, auto_create: e.target.checked })}
                className="rounded"
              />
              <Label htmlFor="auto_create" className="text-sm font-normal cursor-pointer">
                Automatically create connection after setup
              </Label>
            </div>

            <Alert>
              <AlertDescription className="text-sm">
                <strong>What this will do:</strong>
                <ul className="mt-2 ml-4 list-disc text-xs space-y-1">
                  <li>Connect to your server via SSH</li>
                  <li>Locate WordPress installation</li>
                  <li>Install WPGraphQL and JWT Authentication plugins</li>
                  <li>Create an API user with application password</li>
                  <li>Configure JWT authentication</li>
                  <li>Return connection details</li>
                </ul>
              </AlertDescription>
            </Alert>

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Setting up...
                  </>
                ) : (
                  "Setup Remote WordPress"
                )}
              </Button>
            </div>
          </form>
        )}

        {status === "running" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Setting up WordPress...</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
            <Alert>
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription>
                This may take a few minutes. Please don't close this window.
              </AlertDescription>
            </Alert>
          </div>
        )}

        {status === "success" && connectionInfo && (
          <div className="space-y-4">
            <Alert className="border-green-500 bg-green-50">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                <strong>Setup completed successfully!</strong>
                {formData.auto_create && (
                  <p className="mt-1 text-sm">Connection has been automatically added to your list.</p>
                )}
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label>Connection Details</Label>
              <div className="rounded-lg bg-gray-50 p-4 space-y-2 text-sm">
                <div>
                  <span className="font-medium">Name:</span> {connectionInfo.name}
                </div>
                <div>
                  <span className="font-medium">URL:</span> {connectionInfo.wp_url}
                </div>
                <div>
                  <span className="font-medium">GraphQL:</span> {connectionInfo.wp_graphql_endpoint}
                </div>
                <div>
                  <span className="font-medium">User:</span> {connectionInfo.wp_user}
                </div>
                <div>
                  <span className="font-medium">App Password:</span> {connectionInfo.wp_app_password}
                </div>
              </div>
            </div>

            {output && (
              <details className="text-xs">
                <summary className="cursor-pointer font-medium">View Setup Output</summary>
                <pre className="mt-2 rounded bg-gray-900 text-gray-100 p-3 overflow-x-auto">
                  {output}
                </pre>
              </details>
            )}

            <div className="flex justify-end">
              <Button onClick={handleClose}>Done</Button>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Setup failed:</strong>
                <p className="mt-1 text-sm">{errorMessage}</p>
              </AlertDescription>
            </Alert>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={resetForm}>
                Try Again
              </Button>
              <Button onClick={handleClose}>Close</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
