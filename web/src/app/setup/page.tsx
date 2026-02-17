"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

export default function SetupPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleRetry = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/auth/setup-default-connection", {
        method: "POST",
      });
      const result = await response.json();

      if (result.success) {
        toast({
          title: "WordPress connected!",
          description: "Your WordPress connection is ready.",
        });
        router.push("/");
      } else {
        toast({
          variant: "destructive",
          title: "Setup failed",
          description: result.error || "Auto-setup is not configured. Please contact your administrator.",
        });
      }
    } catch (error) {
      console.error("Setup error:", error);
      toast({
        variant: "destructive",
        title: "Setup failed",
        description: "Could not connect to WordPress. Please contact your administrator.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="text-2xl">⚠️ Setup Required</CardTitle>
          <CardDescription>
            WordPress connection could not be configured automatically.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-900 dark:text-amber-100">
              <strong>Auto-setup failed.</strong> This application requires a WordPress connection to be configured by the administrator.
            </p>
          </div>

          <div className="space-y-4">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              If you are a user, please contact your system administrator to complete the setup.
            </p>

            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <p className="text-sm text-blue-900 dark:text-blue-100 mb-3">
                <strong>For Administrators:</strong>
              </p>
              <p className="text-sm text-blue-900 dark:text-blue-100 mb-2">
                Configure the following environment variables in <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">web/.env.local</code>:
              </p>
              <pre className="text-xs bg-blue-100 dark:bg-blue-800 p-3 rounded overflow-x-auto">
{`DEFAULT_WP_NAME=Your WordPress Site
DEFAULT_WP_URL=http://localhost:8080
DEFAULT_WP_GRAPHQL_ENDPOINT=http://localhost:8080/graphql
DEFAULT_WP_USER=admin
DEFAULT_WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx`}
              </pre>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-2">
                <strong>Note:</strong> These URLs are for backend use only. Users never access WordPress directly - all requests are proxied through the Next.js API.
              </p>
            </div>
          </div>

          <div className="pt-4 space-y-3">
            <Button onClick={handleRetry} className="w-full" disabled={loading}>
              {loading ? "Retrying..." : "Retry Auto-Setup"}
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push("/auth")}
              className="w-full"
            >
              Back to Login
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
