"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Users,
  Mail,
  Crown,
  Settings,
  UserPlus,
  UserMinus,
  Shield
} from "lucide-react";

interface Activity {
  id: number;
  user_id: number;
  organization_id: number | null;
  activity_type: string;
  metadata: any;
  created_at: string;
  user_name: string;
  user_username: string | null;
  user_avatar: string | null;
  organization_name: string | null;
  organization_slug: string | null;
}

interface ActivityFeedProps {
  type?: "user" | "organization" | "feed";
  organizationId?: number;
  limit?: number;
}

export function ActivityFeed({ type = "feed", organizationId, limit = 20 }: ActivityFeedProps) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadActivities();
  }, [type, organizationId]);

  async function loadActivities() {
    try {
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) return;

      let url = "http://localhost:8000/activities/feed";
      if (type === "user") {
        url = "http://localhost:8000/activities";
      } else if (type === "organization" && organizationId) {
        url = `http://localhost:8000/organizations/${organizationId}/activities`;
      }

      const response = await fetch(`${url}?limit=${limit}`, {
        headers: {
          "X-Session-ID": sessionId,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setActivities(data);
      }
    } catch (error) {
      console.error("Failed to load activities:", error);
    } finally {
      setIsLoading(false);
    }
  }

  function getActivityIcon(type: string) {
    switch (type) {
      case "profile_updated":
        return <User className="h-4 w-4" />;
      case "profile_avatar_changed":
        return <User className="h-4 w-4" />;
      case "organization_created":
        return <Users className="h-4 w-4" />;
      case "organization_joined":
        return <UserPlus className="h-4 w-4" />;
      case "organization_left":
        return <UserMinus className="h-4 w-4" />;
      case "member_role_changed":
        return <Shield className="h-4 w-4" />;
      case "ownership_transferred":
        return <Crown className="h-4 w-4" />;
      case "invite_sent":
        return <Mail className="h-4 w-4" />;
      case "invite_accepted":
        return <Mail className="h-4 w-4" />;
      default:
        return <Settings className="h-4 w-4" />;
    }
  }

  function getActivityMessage(activity: Activity): string {
    const userName = activity.user_username ? `@${activity.user_username}` : activity.user_name;
    const metadata = activity.metadata || {};

    switch (activity.activity_type) {
      case "profile_updated":
        return `${userName} updated their profile`;
      case "profile_avatar_changed":
        return `${userName} changed their avatar`;
      case "organization_created":
        return `${userName} created ${activity.organization_name}`;
      case "organization_joined":
        return `${userName} joined ${activity.organization_name}`;
      case "organization_left":
        return `${userName} left ${activity.organization_name}`;
      case "member_role_changed":
        return `${userName}'s role was changed to ${metadata.new_role} in ${activity.organization_name}`;
      case "ownership_transferred":
        return `${userName} transferred ownership of ${activity.organization_name}`;
      case "invite_sent":
        return `${userName} invited ${metadata.invitee_email} to ${metadata.organization_name || activity.organization_name}`;
      case "invite_accepted":
        return `${userName} accepted an invite to ${metadata.organization_name || activity.organization_name}`;
      default:
        return `${userName} performed an action`;
    }
  }

  function formatTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-gray-500">
          Loading activities...
        </CardContent>
      </Card>
    );
  }

  if (activities.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-gray-500">
          No activities yet
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {activities.map((activity) => (
        <Card key={activity.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {activity.user_avatar ? (
                <img
                  src={activity.user_avatar}
                  alt={activity.user_name}
                  className="w-10 h-10 rounded-full object-cover"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  <User className="h-5 w-5 text-gray-500" />
                </div>
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary" className="flex items-center gap-1">
                    {getActivityIcon(activity.activity_type)}
                    <span className="text-xs">{activity.activity_type.replace(/_/g, " ")}</span>
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {formatTime(activity.created_at)}
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {getActivityMessage(activity)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
