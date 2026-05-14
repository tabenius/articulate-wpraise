"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useAuth } from "./auth-context";
import { getErrorMessage } from "@/lib/api-contract";

interface Connection {
  id: number;
  name: string;
  wp_url: string;
  wp_graphql_endpoint: string;
  wp_user: string;
  is_active: boolean;
  mcp_api_key?: string | null;
  created_at: string;
}

interface ConnectionContextType {
  connections: Connection[];
  activeConnection: Connection | null;
  isLoading: boolean;
  refreshConnections: () => Promise<void>;
  addConnection: (connection: Omit<Connection, "id" | "is_active" | "created_at"> & { wp_app_password: string }) => Promise<void>;
  updateConnection: (id: number, updates: Partial<Connection>) => Promise<void>;
  deleteConnection: (id: number) => Promise<void>;
  activateConnection: (id: number) => Promise<void>;
}

const ConnectionContext = createContext<ConnectionContextType | undefined>(undefined);

export function ConnectionProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      refreshConnections();
    } else {
      setConnections([]);
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  async function refreshConnections() {
    try {
      setIsLoading(true);
      const response = await fetch("/api/connections");
      
      if (!response.ok) {
        throw new Error("Failed to fetch connections");
      }

      const data = await response.json();
      const payload = Array.isArray(data) ? data : data?.data;
      setConnections(Array.isArray(payload) ? payload : []);
    } catch (error) {
      console.error("Error fetching connections:", error);
      setConnections([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function addConnection(connection: Omit<Connection, "id" | "is_active" | "created_at"> & { wp_app_password: string }) {
    const response = await fetch("/api/connections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(connection),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(getErrorMessage(error) || "Failed to add connection");
    }

    await refreshConnections();
  }

  async function updateConnection(id: number, updates: Partial<Connection>) {
    const response = await fetch(`/api/connections/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(getErrorMessage(error) || "Failed to update connection");
    }

    await refreshConnections();
  }

  async function deleteConnection(id: number) {
    const response = await fetch(`/api/connections/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(getErrorMessage(error) || "Failed to delete connection");
    }

    await refreshConnections();
  }

  async function activateConnection(id: number) {
    const response = await fetch(`/api/connections/${id}/activate`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(getErrorMessage(error) || "Failed to activate connection");
    }

    await refreshConnections();
  }

  const activeConnection = connections.find(conn => conn.is_active) || null;

  return (
    <ConnectionContext.Provider
      value={{
        connections,
        activeConnection,
        isLoading,
        refreshConnections,
        addConnection,
        updateConnection,
        deleteConnection,
        activateConnection,
      }}
    >
      {children}
    </ConnectionContext.Provider>
  );
}

export function useConnections() {
  const context = useContext(ConnectionContext);
  if (context === undefined) {
    throw new Error("useConnections must be used within a ConnectionProvider");
  }
  return context;
}
