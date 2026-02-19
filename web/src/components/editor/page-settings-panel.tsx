"use client";

import { useState } from "react";
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
import { Home, Menu } from "lucide-react";

export function PageSettingsPanel() {
  const currentPost = usePostStore((s) => s.currentPost);
  const { toast } = useToast();

  const [isFrontPage, setIsFrontPage] = useState(false);
  const [inMainMenu, setInMainMenu] = useState(false);

  const handleSetFrontPage = async (checked: boolean) => {
    if (!currentPost) return;

    // TODO: Implement WordPress front page setting via MCP
    toast({
      title: "Coming Soon",
      description: "Front page setting will be available soon",
      variant: "default",
    });

    setIsFrontPage(checked);
  };

  const handleSetInMenu = async (checked: boolean) => {
    if (!currentPost) return;

    // TODO: Implement WordPress menu assignment via MCP
    toast({
      title: "Coming Soon",
      description: "Menu assignment will be available soon",
      variant: "default",
    });

    setInMainMenu(checked);
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
            />
            <Label
              htmlFor="front-page"
              className="text-sm font-normal cursor-pointer"
            >
              Use this page as the front page
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
            />
            <Label
              htmlFor="main-menu"
              className="text-sm font-normal cursor-pointer"
            >
              Add to main navigation menu
            </Label>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            When enabled, this page will appear in your site's primary navigation menu.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
