"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Save, Trash2, AlertTriangle } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ImageUpload } from "@/components/profile/image-upload";

interface Organization {
  id: number;
  name: string;
  slug: string;
  owner_id: number;
  avatar: string | null;
  banner: string | null;
  bio: string | null;
  created_at: string;
}

export default function OrganizationSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const orgId = parseInt(params.id as string);

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    bio: "",
    avatar: "",
    banner: "",
  });

  useEffect(() => {
    loadOrganization();
    checkOwnership();
  }, [orgId]);

  async function loadOrganization() {
    try {
      const response = await fetch(`http://localhost:8000/organizations/${orgId}`);
      if (!response.ok) throw new Error("Failed to load organization");

      const data = await response.json();
      setOrganization(data);
      setFormData({
        name: data.name || "",
        slug: data.slug || "",
        bio: data.bio || "",
        avatar: data.avatar || "",
        banner: data.banner || "",
      });
    } catch (error) {
      toast({
        title: "Failed to load organization",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function checkOwnership() {
    try {
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) return;

      const profileResponse = await fetch("http://localhost:8000/profile", {
        headers: { "X-Session-ID": sessionId },
      });

      if (!profileResponse.ok) return;

      const profile = await profileResponse.json();
      const orgResponse = await fetch(`http://localhost:8000/organizations/${orgId}`);

      if (orgResponse.ok) {
        const org = await orgResponse.json();
        setIsOwner(org.owner_id === profile.id);
      }
    } catch (error) {
      console.error("Failed to check ownership:", error);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(`http://localhost:8000/organizations/${orgId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to update organization");
      }

      toast({
        title: "Settings saved",
        description: "Organization settings have been updated",
      });

      loadOrganization();
    } catch (error) {
      toast({
        title: "Failed to save settings",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(`http://localhost:8000/organizations/${orgId}`, {
        method: "DELETE",
        headers: {
          "X-Session-ID": sessionId || "",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to delete organization");
      }

      toast({
        title: "Organization deleted",
        description: "The organization has been permanently deleted",
      });

      router.push("/organizations");
    } catch (error) {
      toast({
        title: "Failed to delete organization",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading...</p>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="container mx-auto p-6">
        <p>Organization not found</p>
      </div>
    );
  }

  if (!isOwner) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-gray-600">
              Only the organization owner can access settings
            </p>
            <div className="mt-4 text-center">
              <Link href={`/organizations/${orgId}`}>
                <Button variant="outline">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Organization
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <Link href={`/organizations/${orgId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Organization
          </Button>
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-bold">Organization Settings</h1>
        <p className="text-gray-600">{organization.name}</p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>General Information</CardTitle>
              <CardDescription>
                Update your organization's basic information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Banner */}
              <ImageUpload
                currentImage={formData.banner}
                onImageChange={(url) => setFormData({ ...formData, banner: url })}
                type="banner"
                label="Banner Image"
              />

              {/* Avatar */}
              <ImageUpload
                currentImage={formData.avatar}
                onImageChange={(url) => setFormData({ ...formData, avatar: url })}
                type="avatar"
                label="Avatar"
              />

              <div className="space-y-2">
                <Label htmlFor="name">Organization Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Organization"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="slug">URL Slug</Label>
                <Input
                  id="slug"
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  placeholder="my-organization"
                />
                <p className="text-xs text-gray-500">
                  Used in URLs: /organizations/{formData.slug || "slug"}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="bio">Description</Label>
                <Textarea
                  id="bio"
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Tell people about your organization..."
                  rows={4}
                  maxLength={500}
                />
                <p className="text-xs text-gray-500">
                  {formData.bio.length}/500 characters
                </p>
              </div>

              <Button onClick={handleSave} disabled={isSaving}>
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-6">
          <Card className="border-red-200 dark:border-red-800">
            <CardHeader>
              <CardTitle className="text-red-600 dark:text-red-400">Danger Zone</CardTitle>
              <CardDescription>
                Irreversible and destructive actions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border border-red-200 dark:border-red-800 rounded-lg">
                <div>
                  <h3 className="font-medium">Delete Organization</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Permanently delete this organization and all its data
                  </p>
                </div>
                <Button
                  variant="destructive"
                  onClick={() => setDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog} onOpenChange={setDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Delete Organization
            </DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete the{" "}
              <strong>{organization.name}</strong> organization and remove all members and invites.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-sm text-red-800 dark:text-red-200">
                <strong>Warning:</strong> All data associated with this organization will be lost.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDeleteDialog(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Organization
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
