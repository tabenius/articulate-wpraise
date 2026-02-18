"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Search, Users, ArrowLeft, UserPlus } from "lucide-react";
import Link from "next/link";

interface Organization {
  id: number;
  name: string;
  slug: string;
  owner_id: number;
  avatar: string | null;
  banner: string | null;
  bio: string | null;
  visibility: string;
  member_count: number;
  created_at: string;
}

export default function DiscoverOrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    searchOrganizations();
  }, []);

  async function searchOrganizations(query?: string) {
    setIsSearching(true);
    try {
      const searchParam = query !== undefined ? query : searchQuery;
      const url = searchParam
        ? `http://localhost:8000/organizations/search?q=${encodeURIComponent(searchParam)}`
        : "http://localhost:8000/organizations/search";

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to search organizations");

      const data = await response.json();
      setOrganizations(data);
    } catch (error) {
      toast({
        title: "Failed to search organizations",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setIsSearching(false);
    }
  }

  async function handleJoin(orgId: number, orgName: string) {
    try {
      const sessionId = localStorage.getItem("session_id");
      const response = await fetch(`http://localhost:8000/organizations/${orgId}/join`, {
        method: "POST",
        headers: {
          "X-Session-ID": sessionId || "",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to join organization");
      }

      toast({
        title: "Joined organization",
        description: `You are now a member of ${orgName}`,
      });

      // Refresh the list
      searchOrganizations();
    } catch (error) {
      toast({
        title: "Failed to join organization",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    searchOrganizations();
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading...</p>
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

      <div className="mb-6">
        <h1 className="text-3xl font-bold">Discover Organizations</h1>
        <p className="text-gray-600">Find and join public organizations</p>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <Input
            placeholder="Search organizations by name or slug..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" disabled={isSearching}>
            <Search className="mr-2 h-4 w-4" />
            {isSearching ? "Searching..." : "Search"}
          </Button>
        </div>
      </form>

      {/* Results */}
      {organizations.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Users className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium mb-2">No organizations found</h3>
            <p className="text-gray-600">
              {searchQuery ? "Try a different search term" : "No public organizations available"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {organizations.map((org) => (
            <Card key={org.id} className="hover:shadow-lg transition-shadow">
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
                      className="w-12 h-12 rounded-full object-cover"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg truncate">{org.name}</CardTitle>
                    <CardDescription>@{org.slug}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {org.bio && (
                  <p className="text-sm text-gray-600 line-clamp-2">{org.bio}</p>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Users className="h-4 w-4" />
                      {org.member_count}
                    </span>
                    <Badge variant={org.visibility === "public" ? "default" : "secondary"}>
                      {org.visibility}
                    </Badge>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Link href={`/organizations/${org.id}`} className="flex-1">
                    <Button variant="outline" className="w-full" size="sm">
                      View
                    </Button>
                  </Link>
                  {org.visibility === "public" && (
                    <Button
                      onClick={() => handleJoin(org.id, org.name)}
                      className="flex-1"
                      size="sm"
                    >
                      <UserPlus className="mr-2 h-4 w-4" />
                      Join
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
