"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import { Notifications } from "./notifications";
import { OrganizationSwitcher } from "./header/organization-switcher";
import { Button } from "./ui/button";
import { Home, Users, UserCircle, Mail, BookOpen, Layout, Zap, Rocket, Activity } from "lucide-react";

export function Navigation() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Home", icon: Home },
    { href: "/site-editor", label: "Site Editor", icon: Layout },
    { href: "/media-optimizer", label: "Media Optimizer", icon: Zap },
    { href: "/export", label: "Export to Next.js", icon: Rocket },
    { href: "/profiling", label: "Performance", icon: Activity },
    { href: "/organizations", label: "Organizations", icon: Users },
    { href: "/profile", label: "Profile", icon: UserCircle },
    { href: "/invites", label: "Invites", icon: Mail },
  ];

  return (
    <nav className="border-b bg-background">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="font-bold text-xl">
              Articulate
            </Link>
            <div className="hidden md:flex gap-4">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link key={item.href} href={item.href}>
                    <Button
                      variant={isActive ? "default" : "ghost"}
                      size="sm"
                      className="flex items-center gap-2"
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Button>
                  </Link>
                );
              })}
              <a href="http://localhost:8091" target="_blank" rel="noopener noreferrer">
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <BookOpen className="h-4 w-4" />
                  Docs
                </Button>
              </a>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <OrganizationSwitcher />
            <Notifications />
            <ThemeToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
