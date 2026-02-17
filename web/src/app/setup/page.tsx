"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export default function SetupPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: process.env.NEXT_PUBLIC_DEFAULT_WP_NAME || "Local WordPress",
    wp_url: process.env.NEXT_PUBLIC_DEFAULT_WP_URL || "http://localhost:8080",
    wp_graphql_endpoint: process.env.NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT || "http://localhost:8080/graphql",
    wp_user: process.env.NEXT_PUBLIC_DEFAULT_WP_USER || "admin",
    wp_app_password: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch("/api/connections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to add connection");
      }

      toast({
        title: "Connection added!",
        description: "Your WordPress connection is ready to use.",
      });

      // Redirect to main app
      router.push("/");
    } catch (error) {
      console.error("Setup error:", error);
      toast({
        variant: "destructive",
        title: "Setup failed",
        description: error instanceof Error ? error.message : "Failed to add connection",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="text-2xl">Welcome to WP-AI! 🎉</CardTitle>
          <CardDescription>
            Let's connect to your WordPress site to get started.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Connection Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="My WordPress Site"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="wp_url">WordPress URL</Label>
              <Input
                id="wp_url"
                value={formData.wp_url}
                onChange={(e) => setFormData({ ...formData, wp_url: e.target.value })}
                placeholder="http://localhost:8080"
                required
              />
              <p className="text-sm text-gray-500">
                The URL where WordPress is accessible from this frontend.<br/>
                Local: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">http://localhost:8080</code><br/>
                Remote: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">https://yourdomain.com</code> or <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">http://server-ip:8080</code>
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="wp_graphql_endpoint">GraphQL Endpoint</Label>
              <Input
                id="wp_graphql_endpoint"
                value={formData.wp_graphql_endpoint}
                onChange={(e) => setFormData({ ...formData, wp_graphql_endpoint: e.target.value })}
                placeholder="http://localhost:8080/graphql"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="wp_user">WordPress Username</Label>
              <Input
                id="wp_user"
                value={formData.wp_user}
                onChange={(e) => setFormData({ ...formData, wp_user: e.target.value })}
                placeholder="admin"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="wp_app_password">WordPress Application Password</Label>
              <Input
                id="wp_app_password"
                value={formData.wp_app_password}
                onChange={(e) => setFormData({ ...formData, wp_app_password: e.target.value })}
                placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                required
              />
              <div className="text-sm text-gray-500 space-y-1">
                <p>To generate an application password:</p>
                <ol className="list-decimal list-inside ml-2 space-y-1">
                  <li>Go to <a href={`${formData.wp_url}/wp-admin/profile.php`} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">WordPress Admin → Profile</a></li>
                  <li>Scroll to "Application Passwords"</li>
                  <li>Enter name: "WP-AI" and click "Add New Application Password"</li>
                  <li>Copy the generated password (keep the spaces)</li>
                </ol>
              </div>
            </div>

            <div className="pt-4">
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Connecting..." : "Connect WordPress"}
              </Button>
            </div>
          </form>

          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong>Note:</strong> This manual setup is only needed if auto-setup failed.<br/>
              Normally, WP-AI auto-creates the WordPress connection from environment variables.<br/>
              <br/>
              <strong>For Administrators:</strong> Configure <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">NEXT_PUBLIC_DEFAULT_WP_*</code> and
              <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">DEFAULT_WP_APP_PASSWORD</code> in <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">web/.env.local</code>
              to set the default WordPress connection for all users.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
