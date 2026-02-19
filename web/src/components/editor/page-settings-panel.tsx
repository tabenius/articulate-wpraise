"use client";

import { useState, useEffect } from "react";
import { usePostStore } from "@/stores/post-store";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Home, Menu, Loader2 } from "lucide-react";

export function PageSettingsPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const { toast } = useToast();

  const [isFrontPage, setIsFrontPage] = useState(false);
  const [inMainMenu, setInMainMenu] = useState(false);
  const [loading, setLoading] = useState(false);
  const [menusLoading, setMenusLoading] = useState(false);
  const [primaryMenuId, setPrimaryMenuId] = useState<number | null>(null);

  // Check if this page is the front page
  useEffect(() => {
    if (!currentPost) return;

    const checkFrontPage = async () => {
      try {
        const response = await fetch("/api/settings/front-page");
        const data = await response.json();

        if (data.page_on_front === currentPost.id) {
          setIsFrontPage(true);
        }
      } catch (error) {
        console.error("Failed to check front page status:", error);
      }
    };

    checkFrontPage();
  }, [currentPost]);

  // Get primary menu and check if page is in it
  useEffect(() => {
    if (!currentPost) return;

    const checkMenuStatus = async () => {
      try {
        setMenusLoading(true);
        // Get all menus
        const menusResponse = await fetch("/api/menus");
        const menusData = await menusResponse.json();

        if (menusData.success && menusData.menus?.length > 0) {
          // Find primary menu (usually the first one or one with 'primary' location)
          const primaryMenu = menusData.menus.find(
            (m: any) => m.locations?.includes("primary") || m.slug === "primary"
          ) || menusData.menus[0];

          setPrimaryMenuId(primaryMenu.databaseId);

          // Check if current page is in this menu
          const itemsResponse = await fetch(`/api/menus/${primaryMenu.databaseId}/items`);
          const itemsData = await itemsResponse.json();

          if (itemsData.success) {
            const pageInMenu = itemsData.menu?.items?.some(
              (item: any) => item.connectedNode?.node?.databaseId === currentPost.id
            );
            setInMainMenu(pageInMenu || false);
          }
        }
      } catch (error) {
        console.error("Failed to check menu status:", error);
      } finally {
        setMenusLoading(false);
      }
    };

    checkMenuStatus();
  }, [currentPost]);

  const handleSetFrontPage = async (checked: boolean) => {
    if (!currentPost) return;

    setLoading(true);
    try {
      const response = await fetch("/api/settings/front-page", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pageId: checked ? currentPost.id : null,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setIsFrontPage(checked);
        toast({
          title: checked ? "Front page set" : "Front page unset",
          description: checked
            ? `"${currentPost.title}" is now your homepage`
            : "Your site will show latest posts on the homepage",
        });
      } else {
        throw new Error(data.error || "Failed to update front page");
      }
    } catch (error) {
      console.error("Failed to update front page:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update front page",
      });
      setIsFrontPage(!checked); // Revert on error
    } finally {
      setLoading(false);
    }
  };

  const handleSetInMenu = async (checked: boolean) => {
    if (!currentPost || !primaryMenuId) {
      toast({
        variant: "destructive",
        title: "No menu found",
        description: "Please create a primary menu in WordPress first",
      });
      return;
    }

    setLoading(true);
    try {
      if (checked) {
        // Add to menu
        const response = await fetch(`/api/menus/${primaryMenuId}/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pageId: currentPost.id,
            label: currentPost.title,
          }),
        });

        const data = await response.json();

        if (data.success) {
          setInMainMenu(true);
          toast({
            title: "Added to menu",
            description: `"${currentPost.title}" added to navigation menu`,
          });
        } else {
          throw new Error(data.error || data.note || "Failed to add to menu");
        }
      } else {
        // Remove from menu
        const response = await fetch(
          `/api/menus/${primaryMenuId}/items?pageId=${currentPost.id}`,
          { method: "DELETE" }
        );

        const data = await response.json();

        if (data.success) {
          setInMainMenu(false);
          toast({
            title: "Removed from menu",
            description: `"${currentPost.title}" removed from navigation menu`,
          });
        } else {
          throw new Error(data.error || "Failed to remove from menu");
        }
      }
    } catch (error) {
      console.error("Failed to update menu:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update menu",
      });
      setInMainMenu(!checked); // Revert on error
    } finally {
      setLoading(false);
    }
  };

  if (!currentPost) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Home className="h-4 w-4" />
            Front Page
          </CardTitle>
          <CardDescription className="text-xs">
            Set this page as your site's homepage
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="front-page"
              checked={isFrontPage}
              onCheckedChange={handleSetFrontPage}
              disabled={loading}
            />
            <Label
              htmlFor="front-page"
              className="text-sm font-normal cursor-pointer flex items-center gap-2"
            >
              Use this page as the front page
              {loading && <Loader2 className="h-3 w-3 animate-spin" />}
            </Label>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            When enabled, this page will be displayed as your site's homepage instead of the latest posts.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Menu className="h-4 w-4" />
            Navigation Menu
          </CardTitle>
          <CardDescription className="text-xs">
            Add this page to your site's main navigation menu
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="main-menu"
              checked={inMainMenu}
              onCheckedChange={handleSetInMenu}
              disabled={loading || menusLoading || !primaryMenuId}
            />
            <Label
              htmlFor="main-menu"
              className="text-sm font-normal cursor-pointer flex items-center gap-2"
            >
              Add to main navigation menu
              {(loading || menusLoading) && <Loader2 className="h-3 w-3 animate-spin" />}
            </Label>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {menusLoading
              ? "Checking menu status..."
              : !primaryMenuId
              ? "No primary menu found. Create one in WordPress first."
              : "When enabled, this page will appear in your site's primary navigation menu."}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
