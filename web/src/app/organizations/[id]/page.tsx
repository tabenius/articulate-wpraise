"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Mail, Trash2, Crown, Shield, Eye, Users as UsersIcon } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

interface Organization {
  id: number;
  name: string;
  slug: string;
  owner_id: number;
  avatar: string | null;
  banner: string | null;
  bio: string | null;
  member_count: number;
  created_at: string;
}

interface Member {
  id: number;
  user_id: number;
  role: string;
  joined_at: string;
  email: string;
  username: string | null;
  name: string;
  avatar: string | null;
}

interface Invite {
  id: number;
  invitee_email: string;
  role: string;
  status: string;
  token: string;
  expires_at: string;
  created_at: string;
  inviter_name: string;
}

export default function OrganizationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const orgId = parseInt(params.id as string);

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  useEffect(() => {
    loadOrganization();
    loadMembers();
    loadInvites();
  }, [orgId]);

  async function loadOrganization() {
    try {
      const response = await fetch(`http://localhost:8000/organizations/${orgId}`);
      if (!response.ok) throw new Error("Failed to load organization");
      const data = await response.json();
      setOrganization(data);
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

  async function loadMembers() {
    try {
      const response = await fetch(`http://localhost:8000/organizations/${orgId}/members`);
      if (!response.ok) throw new Error("Failed to load members");
      const data = await response.json();
      setMembers(data);
    } catch (error) {
      console.error("Failed to load members:", error);
    }
  }

  async function loadInvites() {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(`http://localhost:8000/organizations/${orgId}/invites`, {
        headers: {
          "X-Session-ID": sessionId || "",
        },
      });
      if (!response.ok) throw new Error("Failed to load invites");
      const data = await response.json();
      setInvites(data);
    } catch (error) {
      console.error("Failed to load invites:", error);
    }
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(`http://localhost:8000/organizations/${orgId}/invites`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to send invite");
      }

      toast({
        title: "Invite sent",
        description: `Invited ${inviteEmail} to join the organization`,
      });

      setIsInviteDialogOpen(false);
      setInviteEmail("");
      setInviteRole("member");
      loadInvites();
    } catch (error) {
      toast({
        title: "Failed to send invite",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleRemoveMember(memberId: number, memberName: string) {
    if (!confirm(`Remove ${memberName} from this organization?`)) return;

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(
        `http://localhost:8000/organizations/${orgId}/members/${memberId}`,
        {
          method: "DELETE",
          headers: {
            "X-Session-ID": sessionId || "",
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to remove member");
      }

      toast({
        title: "Member removed",
        description: `${memberName} has been removed from the organization`,
      });

      loadMembers();
      loadOrganization();
    } catch (error) {
      toast({
        title: "Failed to remove member",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleCancelInvite(inviteId: number, email: string) {
    if (!confirm(`Cancel invite for ${email}?`)) return;

    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(
        `http://localhost:8000/organizations/${orgId}/invites/${inviteId}`,
        {
          method: "DELETE",
          headers: {
            "X-Session-ID": sessionId || "",
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to cancel invite");
      }

      toast({
        title: "Invite cancelled",
        description: `Invite for ${email} has been cancelled`,
      });

      loadInvites();
    } catch (error) {
      toast({
        title: "Failed to cancel invite",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function getRoleIcon(role: string) {
    switch (role) {
      case "owner":
        return <Crown className="h-4 w-4" />;
      case "admin":
        return <Shield className="h-4 w-4" />;
      case "viewer":
        return <Eye className="h-4 w-4" />;
      default:
        return <UsersIcon className="h-4 w-4" />;
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

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <Link href="/organizations">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Organizations
          </Button>
        </Link>
      </div>

      {/* Organization Header */}
      <Card className="mb-6">
        {organization.banner && (
          <img
            src={organization.banner}
            alt={organization.name}
            className="w-full h-48 object-cover rounded-t-lg"
          />
        )}
        <CardHeader>
          <div className="flex items-start gap-4">
            {organization.avatar && (
              <img
                src={organization.avatar}
                alt={organization.name}
                className="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
              />
            )}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">{organization.name}</CardTitle>
                  <CardDescription>@{organization.slug}</CardDescription>
                </div>
                <Button onClick={() => setIsInviteDialogOpen(true)}>
                  <Mail className="mr-2 h-4 w-4" />
                  Invite Members
                </Button>
              </div>
              {organization.bio && (
                <p className="mt-3 text-gray-600">{organization.bio}</p>
              )}
              <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                <span className="flex items-center gap-1">
                  <UsersIcon className="h-4 w-4" />
                  {organization.member_count} member{organization.member_count !== 1 ? "s" : ""}
                </span>
                <span>
                  Created {new Date(organization.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="members" className="space-y-4">
        <TabsList>
          <TabsTrigger value="members">Members ({members.length})</TabsTrigger>
          <TabsTrigger value="invites">Invites ({invites.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="members" className="space-y-4">
          {members.map((member) => (
            <Card key={member.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {member.avatar && (
                      <img
                        src={member.avatar}
                        alt={member.name}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    )}
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-gray-500">
                        {member.username ? `@${member.username}` : member.email}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant={member.role === "owner" ? "default" : "secondary"}>
                      <span className="flex items-center gap-1">
                        {getRoleIcon(member.role)}
                        {member.role}
                      </span>
                    </Badge>

                    {member.role !== "owner" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveMember(member.user_id, member.name)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="invites" className="space-y-4">
          {invites.length === 0 ? (
            <Card>
              <CardContent className="p-6 text-center text-gray-500">
                No pending invites
              </CardContent>
            </Card>
          ) : (
            invites.map((invite) => (
              <Card key={invite.id}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{invite.invitee_email}</p>
                      <p className="text-sm text-gray-500">
                        Invited by {invite.inviter_name} •{" "}
                        {new Date(invite.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{invite.role}</Badge>
                      <Badge variant={invite.status === "pending" ? "outline" : "default"}>
                        {invite.status}
                      </Badge>

                      {invite.status === "pending" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCancelInvite(invite.id, invite.invitee_email)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* Invite Dialog */}
      <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Member</DialogTitle>
            <DialogDescription>
              Send an invitation to join {organization.name}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleInvite} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <select
                id="role"
                className="w-full rounded-md border border-gray-300 p-2"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="viewer">Viewer - Read-only access</option>
                <option value="member">Member - Can edit content</option>
                <option value="admin">Admin - Can manage members</option>
              </select>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsInviteDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Send Invite</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
