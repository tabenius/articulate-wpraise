"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { ImageUpload } from "@/components/profile/image-upload";
import { Edit2, Save, X, Trash2, Eye, EyeOff } from "lucide-react";
import { useRouter } from "next/navigation";

interface Profile {
  id: number;
  email: string;
  username: string | null;
  name: string;
  avatar: string | null;
  banner: string | null;
  bio: string | null;
  visibility: string;
  created_at: string;
  updated_at: string;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { toast } = useToast();
  const router = useRouter();

  const [formData, setFormData] = useState({
    username: "",
    name: "",
    avatar: "",
    banner: "",
    bio: "",
    visibility: "public",
  });

  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    try {
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) {
        router.push("/auth/login");
        return;
      }

      const response = await fetch("http://localhost:8000/profile", {
        headers: {
          "X-Session-ID": sessionId,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load profile");
      }

      const data = await response.json();
      setProfile(data);
      setFormData({
        username: data.username || "",
        name: data.name || "",
        avatar: data.avatar || "",
        banner: data.banner || "",
        bio: data.bio || "",
        visibility: data.visibility || "public",
      });
    } catch (error) {
      toast({
        title: "Failed to load profile",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to update profile");
      }

      const data = await response.json();
      setProfile(data);
      setIsEditing(false);

      toast({
        title: "Profile updated",
        description: "Your profile has been saved successfully",
      });
    } catch (error) {
      toast({
        title: "Failed to save profile",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    const password = prompt("Enter your password to confirm account deletion:");
    if (!password) return;

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/profile", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to delete account");
      }

      toast({
        title: "Account deleted",
        description: "Your account has been permanently deleted",
      });

      localStorage.removeItem("session_id");
      router.push("/");
    } catch (error) {
      toast({
        title: "Failed to delete account",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function handleCancel() {
    setFormData({
      username: profile?.username || "",
      name: profile?.name || "",
      avatar: profile?.avatar || "",
      banner: profile?.banner || "",
      bio: profile?.bio || "",
    });
    setIsEditing(false);
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading profile...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="container mx-auto p-6">
        <p>Profile not found</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Profile</h1>
          <p className="text-gray-600">Manage your account settings</p>
        </div>

        {!isEditing && (
          <Button onClick={() => setIsEditing(true)}>
            <Edit2 className="mr-2 h-4 w-4" />
            Edit Profile
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          {/* Banner */}
          {isEditing ? (
            <ImageUpload
              currentImage={formData.banner}
              onImageChange={(url) => setFormData({ ...formData, banner: url })}
              type="banner"
              label="Banner Image"
            />
          ) : (
            formData.banner && (
              <img
                src={formData.banner}
                alt="Banner"
                className="w-full h-48 object-cover rounded-lg mb-4"
              />
            )
          )}

          {/* Avatar */}
          <div className="flex items-center gap-4">
            {isEditing ? (
              <ImageUpload
                currentImage={formData.avatar}
                onImageChange={(url) => setFormData({ ...formData, avatar: url })}
                type="avatar"
                label="Avatar"
              />
            ) : (
              formData.avatar && (
                <img
                  src={formData.avatar}
                  alt="Avatar"
                  className="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
                />
              )
            )}

            <div>
              <CardTitle>{profile.name}</CardTitle>
              <CardDescription>
                {profile.username ? `@${profile.username}` : profile.email}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  placeholder="Choose a unique username"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                />
                <p className="text-xs text-gray-500">
                  3-50 characters, letters, numbers, dash and underscore only
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Display Name</Label>
                <Input
                  id="name"
                  placeholder="Your name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="bio">Bio</Label>
                <Textarea
                  id="bio"
                  placeholder="Tell us about yourself..."
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  rows={4}
                  maxLength={500}
                />
                <p className="text-xs text-gray-500">
                  {formData.bio.length}/500 characters
                </p>
              </div>

              <div className="space-y-2">
                <Label>Profile Visibility</Label>
                <Tabs
                  value={formData.visibility}
                  onValueChange={(value) => setFormData({ ...formData, visibility: value })}
                >
                  <TabsList className="grid grid-cols-2 w-full max-w-md">
                    <TabsTrigger value="public">
                      <Eye className="mr-2 h-4 w-4" />
                      Public
                    </TabsTrigger>
                    <TabsTrigger value="private">
                      <EyeOff className="mr-2 h-4 w-4" />
                      Private
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
                <p className="text-xs text-gray-500">
                  {formData.visibility === "public"
                    ? "Your profile can be viewed by anyone"
                    : "Only you can view your profile"}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={profile.email} disabled />
                <p className="text-xs text-gray-500">Email cannot be changed</p>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={handleSave} disabled={isSaving}>
                  <Save className="mr-2 h-4 w-4" />
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
                <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label>Username</Label>
                <p className="text-gray-700">
                  {profile.username || <span className="text-gray-400 italic">Not set</span>}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Email</Label>
                <p className="text-gray-700">{profile.email}</p>
              </div>

              <div className="space-y-2">
                <Label>Bio</Label>
                <p className="text-gray-700 whitespace-pre-wrap">
                  {profile.bio || <span className="text-gray-400 italic">No bio yet</span>}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Profile Visibility</Label>
                <p className="text-gray-700 flex items-center gap-2">
                  {profile.visibility === "public" ? (
                    <>
                      <Eye className="h-4 w-4" />
                      Public
                    </>
                  ) : (
                    <>
                      <EyeOff className="h-4 w-4" />
                      Private
                    </>
                  )}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Member Since</Label>
                <p className="text-gray-700">
                  {new Date(profile.created_at).toLocaleDateString()}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="mt-6 border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Danger Zone</CardTitle>
          <CardDescription>Irreversible actions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Delete Account</p>
              <p className="text-sm text-gray-500">
                Permanently delete your account and all associated data
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Account
            </Button>
          </div>

          {showDeleteConfirm && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800 mb-3">
                Are you absolutely sure? This action cannot be undone. All your data including
                organizations, connections, and settings will be permanently deleted.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                >
                  Yes, Delete My Account
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
