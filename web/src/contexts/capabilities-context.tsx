"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useAuth } from "./auth-context";
import { useConnections } from "./connection-context";

interface WPCapabilities {
  wp_user_id: number;
  wp_username: string;
  wp_email: string;
  roles: string[];
  capabilities: string[];
  is_administrator: boolean;
  connection_id: number;
  connection_name: string;
}

interface CapabilitiesContextType {
  capabilities: WPCapabilities | null;
  isLoading: boolean;
  error: string | null;
  hasCapability: (cap: string) => boolean;
  canPerformOperation: (op: string) => boolean;
  refreshCapabilities: () => Promise<void>;
}

// Map MCP operations to required capabilities (mirrors Python OPERATION_CAPABILITIES)
const OPERATION_CAPABILITIES: Record<string, string[]> = {
  create_post: ["edit_posts"],
  update_post: ["edit_posts"],
  delete_post: ["delete_posts"],
  publish_post: ["publish_posts"],
  create_page: ["edit_pages"],
  update_page: ["edit_pages"],
  delete_page: ["delete_pages"],
  publish_page: ["publish_pages"],
  upload_media: ["upload_files"],
  manage_categories: ["manage_categories"],
  manage_tags: ["manage_categories"],
  get_settings: ["manage_options"],
  update_settings: ["manage_options"],
  manage_menus: ["edit_theme_options"],
  manage_templates: ["edit_theme_options"],
  list_users: ["list_users"],
  create_user: ["create_users"],
  update_user_role: ["promote_users"],
};

const CapabilitiesContext = createContext<CapabilitiesContextType | undefined>(undefined);

export function CapabilitiesProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { activeConnection } = useConnections();
  const [capabilities, setCapabilities] = useState<WPCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshCapabilities = useCallback(async () => {
    if (!isAuthenticated || !activeConnection) {
      setCapabilities(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/capabilities");
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Failed to fetch capabilities");
        setCapabilities(null);
      }
    } catch {
      setError("Failed to fetch capabilities");
      setCapabilities(null);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, activeConnection]);

  // Refresh when auth or connection changes
  useEffect(() => {
    refreshCapabilities();
  }, [refreshCapabilities]);

  const hasCapability = useCallback(
    (cap: string): boolean => {
      if (!capabilities) return false;
      if (capabilities.is_administrator) return true;
      return capabilities.capabilities.includes(cap);
    },
    [capabilities]
  );

  const canPerformOperation = useCallback(
    (op: string): boolean => {
      if (!capabilities) return false;
      if (capabilities.is_administrator) return true;
      const required = OPERATION_CAPABILITIES[op];
      if (!required) return true; // unknown operation = allow (WP will enforce)
      return required.every((cap) => capabilities.capabilities.includes(cap));
    },
    [capabilities]
  );

  return (
    <CapabilitiesContext.Provider
      value={{
        capabilities,
        isLoading,
        error,
        hasCapability,
        canPerformOperation,
        refreshCapabilities,
      }}
    >
      {children}
    </CapabilitiesContext.Provider>
  );
}

export function useCapabilities() {
  const context = useContext(CapabilitiesContext);
  if (context === undefined) {
    throw new Error("useCapabilities must be used within a CapabilitiesProvider");
  }
  return context;
}
