"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { ImageUpload } from "@/components/profile/image-upload";
import { Plus, Users, Settings, Mail, Trash2, Search } from "lucide-react";
import Link from "next/link";

interface Organization {
  id: number;
  name: string;
  slug: string;
  owner_id: number;
  avatar: string | null;
  banner: string | null;
  bio: string | null;
  user_role: string;
  member_count: number;
  created_at: string;
}

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    avatar: "",
    banner: "",
    bio: "",
  });

  useEffect(() => {
    loadOrganizations();
  }, []);

  async function loadOrganizations() {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/organizations", {
        headers: {
          "X-Session-ID": sessionId || "",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load organizations");
      }

      const data = await response.json();
      setOrganizations(data);
    } catch (error) {
      toast({
        title: "Failed to load organizations",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateOrganization(e: React.FormEvent) {
    e.preventDefault();

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/organizations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to create organization");
      }

      const data = await response.json();
      setOrganizations([...organizations, data]);
      setIsCreateDialogOpen(false);
      setFormData({
        name: "",
        slug: "",
        avatar: "",
        banner: "",
        bio: "",
      });

      toast({
        title: "Organization created",
        description: `Successfully created ${data.name}`,
      });
    } catch (error) {
      toast({
        title: "Failed to create organization",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function generateSlug(name: string) {
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    setFormData({ ...formData, slug });
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading organizations...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Organizations</h1>
          <p className="text-gray-600">
            Manage your organizations and team memberships
          </p>
        </div>

        <div className="flex gap-2">
          <Link href="/organizations/discover">
            <Button variant="outline">
              <Search className="mr-2 h-4 w-4" />
              Discover
            </Button>
          </Link>

          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Organization
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create Organization</DialogTitle>
              <DialogDescription>
                Create a new organization to collaborate with your team
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateOrganization} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Organization Name *</Label>
                <Input
                  id="name"
                  placeholder="Acme Corporation"
                  value={formData.name}
                  onChange={(e) => {
                    setFormData({ ...formData, name: e.target.value });
                    if (!formData.slug) {
                      generateSlug(e.target.value);
                    }
                  }}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="slug">URL Slug *</Label>
                <Input
                  id="slug"
                  placeholder="acme-corp"
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  required
                />
                <p className="text-xs text-gray-500">
                  Lowercase letters, numbers, and dashes only
                </p>
              </div>

              <ImageUpload
                currentImage={formData.avatar}
                onImageChange={(url) => setFormData({ ...formData, avatar: url })}
                type="avatar"
                label="Organization Avatar"
              />

              <ImageUpload
                currentImage={formData.banner}
                onImageChange={(url) => setFormData({ ...formData, banner: url })}
                type="banner"
                label="Organization Banner"
              />

              <div className="space-y-2">
                <Label htmlFor="bio">Description</Label>
                <Textarea
                  id="bio"
                  placeholder="What does your organization do?"
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  rows={4}
                  maxLength={500}
                />
                <p className="text-xs text-gray-500">
                  {formData.bio.length}/500 characters
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit">Create Organization</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {organizations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No organizations yet</CardTitle>
            <CardDescription>
              Create your first organization to start collaborating with your team
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {organizations.map((org) => (
            <Link key={org.id} href={`/organizations/${org.id}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                {org.banner && (
                  <img
                    src={org.banner}
                    alt={org.name}
                    className="w-full h-32 object-cover rounded-t-lg"
                  />
                )}
                <CardHeader>
                  <div className="flex items-start gap-3">
                    {org.avatar && (
                      <img
                        src={org.avatar}
                        alt={org.name}
                        className="w-16 h-16 rounded-full object-cover border-2 border-gray-200"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <CardTitle className="truncate">{org.name}</CardTitle>
                      <CardDescription className="truncate">
                        @{org.slug}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {org.bio && (
                    <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                      {org.bio}
                    </p>
                  )}

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Users className="h-4 w-4" />
                      <span>{org.member_count} member{org.member_count !== 1 ? "s" : ""}</span>
                    </div>

                    <Badge variant={org.user_role === "owner" ? "default" : "secondary"}>
                      {org.user_role}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
