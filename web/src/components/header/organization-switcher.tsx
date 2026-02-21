"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Building2, Check, Plus } from "lucide-react";
import { useRouter } from "next/navigation";

interface Organization {
  id: number;
  name: string;
  slug: string;
  role: string;
}

export function OrganizationSwitcher() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    loadOrganizations();
  }, []);

  async function loadOrganizations() {
    try {
      const sessionId = localStorage.getItem("session_id");
      if (!sessionId) {
        setIsLoading(false);
        return;
      }

      const response = await fetch("http://localhost:8000/user/organizations", {
        headers: { "X-Session-ID": sessionId },
      });

      if (!response.ok) {
        setIsLoading(false);
        return;
      }

      const data = await response.json();
      setOrganizations(Array.isArray(data) ? data : []);

      // Try to get current org from localStorage or use first org
      const savedOrgId = localStorage.getItem("current_org_id");
      if (savedOrgId) {
        const org = data.find((o: Organization) => o.id === parseInt(savedOrgId));
        if (org) setCurrentOrg(org);
      } else if (data.length > 0) {
        setCurrentOrg(data[0]);
      }
    } catch (error) {
      console.error("Failed to load organizations:", error);
    } finally {
      setIsLoading(false);
    }
  }

  function switchOrganization(org: Organization) {
    setCurrentOrg(org);
    localStorage.setItem("current_org_id", org.id.toString());
    router.push(`/organizations/${org.id}`);
  }

  if (isLoading) {
    return (
      <Button variant="ghost" size="sm" disabled>
        <Building2 className="mr-2 h-4 w-4" />
        Loading...
      </Button>
    );
  }

  if (organizations.length === 0) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.push("/organizations")}
      >
        <Plus className="mr-2 h-4 w-4" />
        Create Organization
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">
          <Building2 className="mr-2 h-4 w-4" />
          {currentOrg ? currentOrg.name : "Select Organization"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>Organizations</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {organizations.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onClick={() => switchOrganization(org)}
            className="cursor-pointer"
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex-1">
                <div className="font-medium">{org.name}</div>
                <div className="text-xs text-muted-foreground capitalize">
                  {org.role}
                </div>
              </div>
              {currentOrg?.id === org.id && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => router.push("/organizations")}
          className="cursor-pointer"
        >
          <Plus className="mr-2 h-4 w-4" />
          Create or Browse Organizations
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
