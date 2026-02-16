"use client";

import { useConnections } from "@/contexts/connection-context";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Database, Check, Plus } from "lucide-react";
import { useRouter } from "next/navigation";

export function ConnectionSwitcher() {
  const { connections, activeConnection, activateConnection, isLoading } = useConnections();
  const router = useRouter();

  if (isLoading) {
    return (
      <Button variant="outline" size="sm" disabled>
        <Database className="mr-2 h-4 w-4" />
        Loading...
      </Button>
    );
  }

  if (connections.length === 0) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => router.push("/connections")}
      >
        <Plus className="mr-2 h-4 w-4" />
        Add Connection
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Database className="mr-2 h-4 w-4" />
          {activeConnection ? activeConnection.name : "Select Connection"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>WordPress Connections</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {connections.map((connection) => (
          <DropdownMenuItem
            key={connection.id}
            onClick={() => {
              if (!connection.is_active) {
                activateConnection(connection.id);
              }
            }}
            className="cursor-pointer"
          >
            <div className="flex items-center justify-between w-full">
              <span>{connection.name}</span>
              {connection.is_active && (
                <Check className="h-4 w-4 text-blue-600" />
              )}
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => router.push("/connections")}
          className="cursor-pointer"
        >
          <Plus className="mr-2 h-4 w-4" />
          Manage Connections
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
