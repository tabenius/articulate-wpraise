"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { Activity, TrendingUp, Clock, AlertCircle, Zap, CheckCircle2 } from "lucide-react";

interface ProfilingStats {
  function_name: string;
  date: string;
  call_count: number;
  avg_time_ms: number;
  min_time_ms: number;
  max_time_ms: number;
  p95_time_ms: number | null;
  p99_time_ms: number | null;
  success_count: number;
  error_count: number;
}

export function ProfilingDashboard() {
  const { toast } = useToast();
  const [stats, setStats] = useState<ProfilingStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState("7"); // days
  const [selectedFunction, setSelectedFunction] = useState<string>("all");

  useEffect(() => {
    loadProfilingStats();
  }, [dateRange, selectedFunction]);

  async function loadProfilingStats() {
    setLoading(true);
    try {
      const sessionId = localStorage.getItem("sessionId");
      const currentOrgId = localStorage.getItem("currentOrganizationId");

      if (!sessionId) {
        throw new Error("No session");
      }

      // Calculate date range
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - parseInt(dateRange));

      const response = await fetch("http://localhost:8000/profiling/stats", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          organization_id: currentOrgId ? parseInt(currentOrgId) : null,
          function_name: selectedFunction === "all" ? null : selectedFunction,
          start_date: startDate.toISOString().split("T")[0],
          end_date: endDate.toISOString().split("T")[0],
          limit: 100,
        }),
      });

      const data = await response.json();

      if (data.success && data.stats) {
        setStats(data.stats);
      } else {
        throw new Error(data.error || "Failed to load profiling stats");
      }
    } catch (error) {
      toast({
        title: "Error loading profiling data",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  // Aggregate stats across all dates for each function
  const functionStats = stats.reduce((acc, stat) => {
    if (!acc[stat.function_name]) {
      acc[stat.function_name] = {
        function_name: stat.function_name,
        total_calls: 0,
        total_time: 0,
        avg_time: 0,
        max_time: 0,
        total_success: 0,
        total_errors: 0,
      };
    }

    acc[stat.function_name].total_calls += stat.call_count;
    acc[stat.function_name].total_time += stat.avg_time_ms * stat.call_count;
    acc[stat.function_name].max_time = Math.max(acc[stat.function_name].max_time, stat.max_time_ms);
    acc[stat.function_name].total_success += stat.success_count;
    acc[stat.function_name].total_errors += stat.error_count;

    return acc;
  }, {} as Record<string, any>);

  // Calculate average for each function
  Object.values(functionStats).forEach((stat: any) => {
    stat.avg_time = stat.total_calls > 0 ? stat.total_time / stat.total_calls : 0;
  });

  const sortedFunctions = Object.values(functionStats).sort(
    (a: any, b: any) => b.avg_time - a.avg_time
  );

  // Get unique function names for filter
  const uniqueFunctions = Array.from(new Set(stats.map((s) => s.function_name)));

  // Calculate summary metrics
  const totalCalls = stats.reduce((sum, s) => sum + s.call_count, 0);
  const totalErrors = stats.reduce((sum, s) => sum + s.error_count, 0);
  const avgExecutionTime =
    stats.length > 0
      ? stats.reduce((sum, s) => sum + s.avg_time_ms, 0) / stats.length
      : 0;
  const slowestFunction = sortedFunctions[0];

  function formatTime(ms: number): string {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  }

  function getPerformanceColor(avgTime: number): string {
    if (avgTime < 100) return "text-green-600";
    if (avgTime < 1000) return "text-yellow-600";
    return "text-red-600";
  }

  function getPerformanceBadge(avgTime: number): string {
    if (avgTime < 100) return "Fast";
    if (avgTime < 1000) return "Moderate";
    return "Slow";
  }

  function getPerformanceBadgeVariant(avgTime: number): "default" | "secondary" | "destructive" {
    if (avgTime < 100) return "default";
    if (avgTime < 1000) return "secondary";
    return "destructive";
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCalls.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Last {dateRange} days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Execution</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatTime(avgExecutionTime)}</div>
            <p className="text-xs text-muted-foreground">
              Average across all functions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalCalls > 0
                ? ((1 - totalErrors / totalCalls) * 100).toFixed(1)
                : "100"}
              %
            </div>
            <p className="text-xs text-muted-foreground">
              {totalErrors} errors
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Slowest Function</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-bold truncate">
              {slowestFunction?.function_name || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">
              {slowestFunction ? formatTime(slowestFunction.avg_time) : "No data"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Last 24 hours</SelectItem>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1">
          <Select value={selectedFunction} onValueChange={setSelectedFunction}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Functions</SelectItem>
              {uniqueFunctions.map((fn) => (
                <SelectItem key={fn} value={fn}>
                  {fn}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="detailed">Detailed Stats</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Function Performance</CardTitle>
              <CardDescription>
                Average execution time by function (sorted by slowest)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {sortedFunctions.map((func: any) => (
                    <div
                      key={func.function_name}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-sm">{func.function_name}</h4>
                          <Badge variant={getPerformanceBadgeVariant(func.avg_time)}>
                            {getPerformanceBadge(func.avg_time)}
                          </Badge>
                        </div>
                        <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
                          <span>{func.total_calls} calls</span>
                          <span>
                            {func.total_success} success / {func.total_errors} errors
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${getPerformanceColor(func.avg_time)}`}>
                          {formatTime(func.avg_time)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          max: {formatTime(func.max_time)}
                        </div>
                      </div>
                    </div>
                  ))}

                  {sortedFunctions.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      No profiling data available for selected filters
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Detailed Stats Tab */}
        <TabsContent value="detailed" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Daily Statistics</CardTitle>
              <CardDescription>
                Detailed daily performance metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-2">
                  {stats.map((stat, idx) => (
                    <div
                      key={`${stat.function_name}-${stat.date}-${idx}`}
                      className="p-3 border rounded-lg"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h4 className="font-medium text-sm">{stat.function_name}</h4>
                          <p className="text-xs text-muted-foreground">{stat.date}</p>
                        </div>
                        <Badge variant="outline">{stat.call_count} calls</Badge>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">Avg:</span>{" "}
                          <span className="font-medium">{formatTime(stat.avg_time_ms)}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Min:</span>{" "}
                          <span className="font-medium">{formatTime(stat.min_time_ms)}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Max:</span>{" "}
                          <span className="font-medium">{formatTime(stat.max_time_ms)}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Success:</span>{" "}
                          <span className="font-medium text-green-600">
                            {stat.success_count}
                          </span>
                          {stat.error_count > 0 && (
                            <>
                              {" / "}
                              <span className="font-medium text-red-600">
                                {stat.error_count} errors
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {(stat.p95_time_ms || stat.p99_time_ms) && (
                        <div className="flex gap-4 mt-2 text-xs">
                          {stat.p95_time_ms && (
                            <div>
                              <span className="text-muted-foreground">P95:</span>{" "}
                              <span className="font-medium">
                                {formatTime(stat.p95_time_ms)}
                              </span>
                            </div>
                          )}
                          {stat.p99_time_ms && (
                            <div>
                              <span className="text-muted-foreground">P99:</span>{" "}
                              <span className="font-medium">
                                {formatTime(stat.p99_time_ms)}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}

                  {stats.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      No detailed statistics available
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
