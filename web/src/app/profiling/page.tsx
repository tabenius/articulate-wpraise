"use client";

import { ProfilingDashboard } from "@/components/profiling/profiling-dashboard";

export default function ProfilingPage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Performance Profiling</h1>
          <p className="text-muted-foreground mt-2">
            Monitor MCP function performance and identify bottlenecks
          </p>
        </div>

        <ProfilingDashboard />
      </div>
    </div>
  );
}
