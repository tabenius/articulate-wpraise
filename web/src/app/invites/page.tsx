"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Check, X, Mail } from "lucide-react";

interface Invite {
  id: number;
  organization_id: number;
  invitee_email: string;
  role: string;
  status: string;
  token: string;
  expires_at: string;
  created_at: string;
  org_name: string;
  org_avatar: string | null;
  org_bio: string | null;
  inviter_name: string;
  inviter_email: string;
}

export default function InvitesPage() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    loadInvites();
  }, []);

  async function loadInvites() {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/invites", {
        headers: {
          "X-Session-ID": sessionId || "",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load invites");
      }

      const data = await response.json();
      setInvites(data);
    } catch (error) {
      toast({
        title: "Failed to load invites",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAccept(token: string, orgName: string) {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/invites/accept", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to accept invite");
      }

      toast({
        title: "Invite accepted",
        description: `You are now a member of ${orgName}`,
      });

      loadInvites();
    } catch (error) {
      toast({
        title: "Failed to accept invite",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  async function handleReject(token: string, orgName: string) {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch("http://localhost:8000/invites/reject", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId || "",
        },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to reject invite");
      }

      toast({
        title: "Invite rejected",
        description: `Declined invitation to ${orgName}`,
      });

      loadInvites();
    } catch (error) {
      toast({
        title: "Failed to reject invite",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading invites...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Invites</h1>
        <p className="text-gray-600">
          Manage your organization invitations
        </p>
      </div>

      {invites.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No pending invites</CardTitle>
            <CardDescription>
              You don't have any pending organization invitations
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-4">
          {invites.map((invite) => {
            const isExpired = new Date(invite.expires_at) < new Date();

            return (
              <Card key={invite.id}>
                <CardHeader>
                  <div className="flex items-start gap-4">
                    {invite.org_avatar && (
                      <img
                        src={invite.org_avatar}
                        alt={invite.org_name}
                        className="w-16 h-16 rounded-full object-cover border-2 border-gray-200"
                      />
                    )}
                    <div className="flex-1">
                      <CardTitle>{invite.org_name}</CardTitle>
                      <CardDescription>
                        <span className="flex items-center gap-2 mt-1">
                          <Mail className="h-4 w-4" />
                          Invited by {invite.inviter_name} ({invite.inviter_email})
                        </span>
                      </CardDescription>
                      {invite.org_bio && (
                        <p className="mt-2 text-sm text-gray-600">
                          {invite.org_bio}
                        </p>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge>{invite.role}</Badge>
                      {isExpired && <Badge variant="destructive">Expired</Badge>}
                      <span className="text-sm text-gray-500">
                        {isExpired
                          ? `Expired ${new Date(invite.expires_at).toLocaleDateString()}`
                          : `Expires ${new Date(invite.expires_at).toLocaleDateString()}`}
                      </span>
                    </div>

                    {!isExpired && invite.status === "pending" && (
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReject(invite.token, invite.org_name)}
                        >
                          <X className="mr-2 h-4 w-4" />
                          Decline
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleAccept(invite.token, invite.org_name)}
                        >
                          <Check className="mr-2 h-4 w-4" />
                          Accept
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
