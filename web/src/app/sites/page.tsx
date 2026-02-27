"use client";

import { useState, useEffect, useCallback } from "react";
import { Navigation } from "@/components/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useCapabilities } from "@/contexts/capabilities-context";
import {
  Plus,
  Trash2,
  Globe,
  ExternalLink,
  Loader2,
  Server,
  Eye,
  Link2,
  Shield,
} from "lucide-react";

interface Tenant {
  id: string;
  name: string;
  domain: string;
  default_view: string;
  status: string;
  role?: string;
  created_at: string;
}

interface CustomDomain {
  id: number;
  external_domain: string;
  target_view: string;
  verified: boolean;
}

const VIEWS = ["wordpress", "faust", "astro"] as const;
type View = (typeof VIEWS)[number];

const VIEW_LABELS: Record<View, string> = {
  wordpress: "WordPress",
  faust: "Faust (Next.js)",
  astro: "Astro",
};

const STATUS_COLORS: Record<string, string> = {
  running: "bg-green-500/10 text-green-700 border-green-200",
  provisioning: "bg-yellow-500/10 text-yellow-700 border-yellow-200",
  stopped: "bg-gray-500/10 text-gray-600 border-gray-200",
  error: "bg-red-500/10 text-red-700 border-red-200",
};

export default function SitesPage() {
  const { toast } = useToast();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");

  const loadTenants = useCallback(async () => {
    try {
      const res = await fetch("/api/tenants");
      if (!res.ok) throw new Error("Failed to load sites");
      const data = await res.json();
      setTenants(data.tenants || []);
    } catch (error) {
      toast({
        title: "Failed to load sites",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;

    setIsCreating(true);
    try {
      const res = await fetch("/api/tenants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim().toLowerCase() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create site");

      toast({ title: "Site created", description: `${data.name}.ragbaz.xyz is now running` });
      setIsCreateOpen(false);
      setNewName("");
      loadTenants();
    } catch (error) {
      toast({
        title: "Failed to create site",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDelete(tenant: Tenant) {
    if (!confirm(`Delete "${tenant.name}" and all its containers? This cannot be undone.`)) return;

    try {
      const res = await fetch(`/api/tenants/${tenant.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete site");

      toast({ title: "Site deleted", description: `${tenant.name} has been removed` });
      loadTenants();
    } catch (error) {
      toast({
        title: "Failed to delete site",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleDefaultViewChange(tenant: Tenant, view: string) {
    try {
      const res = await fetch(`/api/tenants/${tenant.id}/default-view`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ default_view: view }),
      });
      if (!res.ok) throw new Error("Failed to update default view");

      toast({ title: "Default view updated", description: `${tenant.name}.ragbaz.xyz now points to ${VIEW_LABELS[view as View]}` });
      loadTenants();
    } catch (error) {
      toast({
        title: "Failed to update",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  if (isLoading) {
    return (
      <>
        <Navigation />
        <div className="container mx-auto p-6 flex items-center justify-center min-h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </>
    );
  }

  return (
    <>
      <Navigation />
      <div className="container mx-auto p-6">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Sites</h1>
            <p className="text-muted-foreground mt-1">
              Manage your WordPress tenant sites and their frontend views
            </p>
          </div>

          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Site
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Site</DialogTitle>
                <DialogDescription>
                  This will provision a WordPress instance with Faust and Astro frontends
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="site-name">Site Name</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="site-name"
                      placeholder="my-site"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                      pattern="^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
                      required
                    />
                    <span className="text-sm text-muted-foreground whitespace-nowrap">.ragbaz.xyz</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Lowercase letters, numbers, and hyphens only. This becomes your subdomain.
                  </p>
                </div>
                <div className="rounded-lg border p-3 space-y-1 text-sm">
                  <p className="font-medium">This will create:</p>
                  <ul className="text-muted-foreground space-y-0.5 ml-4 list-disc">
                    <li>WordPress at wordpress.{newName || "name"}.ragbaz.xyz</li>
                    <li>Faust (Next.js) at faust.{newName || "name"}.ragbaz.xyz</li>
                    <li>Astro SSR at astro.{newName || "name"}.ragbaz.xyz</li>
                    <li>Dedicated MariaDB database</li>
                  </ul>
                </div>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isCreating || !newName.trim()}>
                    {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {isCreating ? "Provisioning..." : "Create Site"}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {tenants.length === 0 ? (
          <Card>
            <CardHeader className="text-center py-12">
              <Server className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <CardTitle>No sites yet</CardTitle>
              <CardDescription>
                Create your first site to get started with multi-tenant WordPress hosting
              </CardDescription>
              <Button className="mt-4 mx-auto" onClick={() => setIsCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Your First Site
              </Button>
            </CardHeader>
          </Card>
        ) : (
          <div className="grid gap-6">
            {tenants.map((tenant) => (
              <TenantCard
                key={tenant.id}
                tenant={tenant}
                onDelete={() => handleDelete(tenant)}
                onDefaultViewChange={(view) => handleDefaultViewChange(tenant, view)}
                onDomainsChanged={loadTenants}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function TenantCard({
  tenant,
  onDelete,
  onDefaultViewChange,
  onDomainsChanged,
}: {
  tenant: Tenant;
  onDelete: () => void;
  onDefaultViewChange: (view: string) => void;
  onDomainsChanged: () => void;
}) {
  const { toast } = useToast();
  const { capabilities } = useCapabilities();
  const [isAddDomainOpen, setIsAddDomainOpen] = useState(false);
  const [domainForm, setDomainForm] = useState({ external_domain: "", target_view: "wordpress" });
  const [isAddingDomain, setIsAddingDomain] = useState(false);
  const [isWpAdminLoading, setIsWpAdminLoading] = useState(false);

  async function handleWpAdmin() {
    setIsWpAdminLoading(true);
    try {
      const res = await fetch("/api/auth/wp-login-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_id: tenant.id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to generate login token");

      // Open WP-Admin with the one-time token
      const wpLoginUrl = `https://wordpress.${tenant.name}.ragbaz.xyz/wp-login.php?articulate_token=${data.token}`;
      window.open(wpLoginUrl, "_blank");
    } catch (error) {
      toast({
        title: "WP Admin access failed",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsWpAdminLoading(false);
    }
  }

  async function handleAddDomain(e: React.FormEvent) {
    e.preventDefault();
    setIsAddingDomain(true);
    try {
      const res = await fetch(`/api/tenants/${tenant.id}/domains`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(domainForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to add domain");

      toast({ title: "Domain added", description: `${domainForm.external_domain} mapped successfully` });
      setIsAddDomainOpen(false);
      setDomainForm({ external_domain: "", target_view: "wordpress" });
      onDomainsChanged();
    } catch (error) {
      toast({
        title: "Failed to add domain",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsAddingDomain(false);
    }
  }

  const statusColor = STATUS_COLORS[tenant.status] || STATUS_COLORS.stopped;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <CardTitle className="text-xl">{tenant.name}</CardTitle>
              <Badge variant="outline" className={statusColor}>
                {tenant.status}
              </Badge>
              {tenant.role && (
                <Badge variant="secondary" className="text-xs">
                  {tenant.role}
                </Badge>
              )}
              {capabilities && capabilities.roles.length > 0 && (
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  WP: {capabilities.roles.join(", ")}
                </span>
              )}
            </div>
            <CardDescription className="flex items-center gap-1">
              <Globe className="h-3.5 w-3.5" />
              {tenant.domain}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleWpAdmin}
              disabled={isWpAdminLoading || tenant.status !== "running"}
            >
              <Shield className="h-4 w-4 mr-1" />
              {isWpAdminLoading ? "Opening..." : "WP Admin"}
            </Button>
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Views */}
        <div>
          <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Eye className="h-4 w-4" />
            Frontend Views
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {VIEWS.map((view) => {
              const isDefault = tenant.default_view === view;
              const subdomain = `${view}.${tenant.name}.ragbaz.xyz`;
              return (
                <div
                  key={view}
                  className={`rounded-lg border p-3 ${isDefault ? "border-primary bg-primary/5" : ""}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{VIEW_LABELS[view]}</span>
                    {isDefault && (
                      <Badge variant="default" className="text-[10px] px-1.5 py-0">
                        default
                      </Badge>
                    )}
                  </div>
                  <a
                    href={`https://${subdomain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1"
                  >
                    {subdomain}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              );
            })}
          </div>
        </div>

        {/* Default View Selector */}
        <div className="flex items-center gap-4">
          <Label className="text-sm whitespace-nowrap">
            Default view for {tenant.name}.ragbaz.xyz:
          </Label>
          <Select value={tenant.default_view} onValueChange={onDefaultViewChange}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {VIEWS.map((view) => (
                <SelectItem key={view} value={view}>
                  {VIEW_LABELS[view]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Custom Domains */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Link2 className="h-4 w-4" />
              Custom Domains
            </h3>
            <Dialog open={isAddDomainOpen} onOpenChange={setIsAddDomainOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="mr-1 h-3 w-3" />
                  Add Domain
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Custom Domain</DialogTitle>
                  <DialogDescription>
                    Point an external domain to one of your site views
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleAddDomain} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Domain</Label>
                    <Input
                      placeholder="example.com"
                      value={domainForm.external_domain}
                      onChange={(e) => setDomainForm({ ...domainForm, external_domain: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Target View</Label>
                    <Select
                      value={domainForm.target_view}
                      onValueChange={(v) => setDomainForm({ ...domainForm, target_view: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VIEWS.map((view) => (
                          <SelectItem key={view} value={view}>
                            {VIEW_LABELS[view]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="rounded-lg border p-3 text-xs text-muted-foreground space-y-1">
                    <p className="font-medium text-foreground">DNS Setup Required:</p>
                    <p>Add a CNAME record pointing <strong>{domainForm.external_domain || "your-domain.com"}</strong> to <strong>{tenant.domain}</strong></p>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setIsAddDomainOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={isAddingDomain}>
                      {isAddingDomain && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Add Domain
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
          <p className="text-xs text-muted-foreground">
            No custom domains configured. Add one to use your own domain name.
          </p>
        </div>

        {/* Metadata */}
        <div className="text-xs text-muted-foreground pt-2 border-t">
          Created {new Date(tenant.created_at).toLocaleDateString()} at {new Date(tenant.created_at).toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
}
