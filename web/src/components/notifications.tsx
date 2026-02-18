"use client";

import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { useRouter } from "next/navigation";

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
  inviter_name: string;
}

export function Notifications() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const router = useRouter();

  useEffect(() => {
    loadInvites();
    // Poll for new invites every 30 seconds
    const interval = setInterval(loadInvites, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadInvites() {
    try {
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) return;

      const response = await fetch("http://localhost:8000/invites", {
        headers: {
          "X-Session-ID": sessionId,
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Only count pending invites
        const pending = data.filter((inv: Invite) => inv.status === "pending");
        setInvites(pending);
        setUnreadCount(pending.length);
      }
    } catch (error) {
      console.error("Failed to load invites:", error);
    }
  }

  function formatTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="p-2 border-b">
          <h3 className="font-semibold">Notifications</h3>
          {unreadCount > 0 && (
            <p className="text-xs text-gray-500">{unreadCount} pending invite{unreadCount !== 1 ? "s" : ""}</p>
          )}
        </div>

        {invites.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            No new notifications
          </div>
        ) : (
          <div className="max-h-96 overflow-y-auto">
            {invites.map((invite) => (
              <DropdownMenuItem
                key={invite.id}
                className="p-3 cursor-pointer"
                onClick={() => router.push("/invites")}
              >
                <div className="flex items-start gap-3 w-full">
                  {invite.org_avatar ? (
                    <img
                      src={invite.org_avatar}
                      alt={invite.org_name}
                      className="w-10 h-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{invite.org_name}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Invited by {invite.inviter_name} · {formatTimeAgo(invite.created_at)}
                    </p>
                    <Badge variant="secondary" className="mt-1 text-xs">
                      {invite.role}
                    </Badge>
                  </div>
                </div>
              </DropdownMenuItem>
            ))}
          </div>
        )}

        {invites.length > 0 && (
          <div className="p-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => router.push("/invites")}
            >
              View all invites
            </Button>
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
