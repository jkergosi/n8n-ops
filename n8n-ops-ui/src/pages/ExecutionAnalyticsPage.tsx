// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '@/lib/api';
import { useAppStore } from '@/store/use-app-store';
import { Search, RefreshCw, AlertTriangle, CheckCircle2, XCircle, Clock, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import type { WorkflowAnalytics, ExecutionAnalyticsEnvelope } from '@/types';
import { getDefaultEnvironmentId, resolveEnvironment, sortEnvironments } from '@/lib/environment-utils';

type TimePreset = '24h' | '7d' | '30d' | 'custom';

export function ExecutionAnalyticsPage() {
  useEffect(() => {
    document.title = 'Execution Analytics - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);

  const selectedEnvironment = useAppStore((state) => state.selectedEnvironment);
  const setSelectedEnvironment = useAppStore((state) => state.setSelectedEnvironment);

  const [timePreset, setTimePreset] = useState<TimePreset>('24h');
  const [customFromDate, setCustomFromDate] = useState('');
  const [customToDate, setCustomToDate] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 100;

  // Fetch environments
  const { data: environments } = useQuery({
    queryKey: ['environments'],
    queryFn: () => api.getEnvironments(),
  });

  // Get available environments for the tenant (filtered and sorted)
  const availableEnvironments = useMemo(() => {
    if (!environments?.data) return [];
    return sortEnvironments(environments.data.filter((env) => env.isActive));
  }, [environments]);

  // Resolve current environment
  const currentEnvironment = resolveEnvironment(environments?.data, selectedEnvironment);

  // Set default environment if none selected and environments are available
  useEffect(() => {
    if (availableEnvironments.length === 0) return;
    const resolved = resolveEnvironment(availableEnvironments, selectedEnvironment);
    const nextId = resolved?.id || getDefaultEnvironmentId(availableEnvironments);
    if (nextId && selectedEnvironment !== nextId) {
      setSelectedEnvironment(nextId);
    }
  }, [availableEnvironments, selectedEnvironment, setSelectedEnvironment]);

  // Calculate time range based on preset
  const { fromTime, toTime, isValidRange } = useMemo(() => {
    const now = new Date();
    let from: Date;
    let to = now;

    if (timePreset === 'custom') {
      if (!customFromDate || !customToDate) {
        return { fromTime: '', toTime: '', isValidRange: false };
      }
      from = new Date(customFromDate);
      to = new Date(customToDate);

      // Validate custom range
      if (from >= to) {
        return { fromTime: '', toTime: '', isValidRange: false };
      }

      // Check 30-day limit
      const diffDays = (to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        return { fromTime: '', toTime: '', isValidRange: false };
      }
    } else {
      // Preset ranges
      const hoursMap = {
        '24h': 24,
        '7d': 24 * 7,
        '30d': 24 * 30,
      };
      const hours = hoursMap[timePreset];
      from = new Date(now.getTime() - hours * 60 * 60 * 1000);
    }

    return {
      fromTime: from.toISOString(),
      toTime: to.toISOString(),
      isValidRange: true,
    };
  }, [timePreset, customFromDate, customToDate]);

  // Fetch analytics data
  const {
    data: analyticsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['execution-analytics', currentEnvironment?.id, fromTime, toTime, currentPage, searchQuery],
    queryFn: async () => {
      if (!currentEnvironment?.id || !isValidRange) {
        return null;
      }

      const result = await api.getExecutionAnalytics({
        environmentId: currentEnvironment.id,
        fromTime,
        toTime,
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        search: searchQuery.length >= 3 ? searchQuery : undefined,
      });

      return result.data;
    },
    enabled: !!currentEnvironment?.id && isValidRange,
    retry: 1,
  });

  // Handle search with debouncing
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(searchInput);
      setCurrentPage(1); // Reset to first page on search
    }, 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Format duration for display
  const formatDuration = (ms: number | null) => {
    if (ms === null || ms === undefined) return 'N/A';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  // Format percentage
  const formatPercentage = (rate: number | null) => {
    if (rate === null || rate === undefined) return 'N/A';
    return `${(rate * 100).toFixed(1)}%`;
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleString();
  };

  // Truncate error message
  const truncateError = (error: string | null, maxLength: number = 100) => {
    if (!error) return 'No error details';
    if (error.length <= maxLength) return error;
    return error.substring(0, maxLength) + '...';
  };

  const handleRefresh = () => {
    refetch();
    toast.success('Analytics refreshed');
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Execution Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Workflow health metrics and execution statistics
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isLoading} variant="outline">
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Select environment and time range for analytics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Environment Selector */}
            <div className="space-y-2">
              <Label htmlFor="environment">Environment</Label>
              <Select
                value={currentEnvironment?.id || ''}
                onValueChange={(value) => {
                  setSelectedEnvironment(value);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger id="environment">
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {availableEnvironments.map((env) => (
                    <SelectItem key={env.id} value={env.id}>
                      {env.n8nName || env.name}
                      {env.n8nType && <span className="text-muted-foreground ml-2">({env.n8nType})</span>}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Time Preset Selector */}
            <div className="space-y-2">
              <Label htmlFor="timePreset">Time Range</Label>
              <Select
                value={timePreset}
                onValueChange={(value: TimePreset) => {
                  setTimePreset(value);
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger id="timePreset">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="24h">Last 24 Hours</SelectItem>
                  <SelectItem value="7d">Last 7 Days</SelectItem>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                  <SelectItem value="custom">Custom Range</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Search */}
            <div className="space-y-2">
              <Label htmlFor="search">Search Workflows</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Min 3 characters..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-8"
                />
              </div>
              {searchInput.length > 0 && searchInput.length < 3 && (
                <p className="text-xs text-muted-foreground">Enter at least 3 characters to search</p>
              )}
            </div>
          </div>

          {/* Custom Date Range */}
          {timePreset === 'custom' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 p-4 border rounded-md">
              <div className="space-y-2">
                <Label htmlFor="fromDate">From Date</Label>
                <Input
                  id="fromDate"
                  type="datetime-local"
                  value={customFromDate}
                  onChange={(e) => {
                    setCustomFromDate(e.target.value);
                    setCurrentPage(1);
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="toDate">To Date</Label>
                <Input
                  id="toDate"
                  type="datetime-local"
                  value={customToDate}
                  onChange={(e) => {
                    setCustomToDate(e.target.value);
                    setCurrentPage(1);
                  }}
                />
              </div>
              {!isValidRange && customFromDate && customToDate && (
                <div className="col-span-2">
                  <Badge variant="destructive">
                    <AlertTriangle className="mr-1 h-3 w-3" />
                    Invalid range: Must be valid dates with max 30 day window
                  </Badge>
                </div>
              )}
            </div>
          )}

          {/* Metadata Display */}
          {analyticsData && (
            <div className="text-xs text-muted-foreground border-t pt-4">
              <p>
                Generated at: {formatTimestamp(analyticsData.generated_at)} |
                Time window: {analyticsData.time_window_days} day{analyticsData.time_window_days !== 1 ? 's' : ''} |
                Results: {analyticsData.items.length}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Analytics</CardTitle>
          <CardDescription>
            Sorted by failures (descending), then total runs (descending)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Loading analytics...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center py-8 text-destructive">
              <AlertTriangle className="h-6 w-6 mr-2" />
              <span>Failed to load analytics: {error.message}</span>
            </div>
          )}

          {!isLoading && !error && !analyticsData?.items?.length && (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <p>No execution data found for the selected time range</p>
            </div>
          )}

          {!isLoading && !error && analyticsData?.items?.length > 0 && (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Workflow</TableHead>
                    <TableHead className="text-center">Runs</TableHead>
                    <TableHead className="text-center">Success %</TableHead>
                    <TableHead className="text-center">Failures</TableHead>
                    <TableHead className="text-right">Avg Duration</TableHead>
                    <TableHead className="text-right">P50</TableHead>
                    <TableHead className="text-right">P95</TableHead>
                    <TableHead>Last Failure</TableHead>
                    <TableHead>Error</TableHead>
                    <TableHead>Failed Node</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analyticsData.items.map((workflow) => (
                    <TableRow key={workflow.workflowId}>
                      <TableCell className="font-medium">
                        <div className="flex flex-col">
                          <span>{workflow.workflowName}</span>
                          <span className="text-xs text-muted-foreground">{workflow.workflowId}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="outline">{workflow.totalRuns}</Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant={
                            workflow.successRate === null
                              ? 'outline'
                              : workflow.successRate >= 0.95
                              ? 'default'
                              : workflow.successRate >= 0.8
                              ? 'secondary'
                              : 'destructive'
                          }
                        >
                          {workflow.successRate === null ? (
                            <CheckCircle2 className="h-3 w-3" />
                          ) : (
                            formatPercentage(workflow.successRate)
                          )}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {workflow.failureRuns > 0 ? (
                          <Badge variant="destructive">
                            <XCircle className="mr-1 h-3 w-3" />
                            {workflow.failureRuns}
                          </Badge>
                        ) : (
                          <Badge variant="outline">0</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatDuration(workflow.avgDurationMs)}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatDuration(workflow.p50DurationMs)}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatDuration(workflow.p95DurationMs)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {formatTimestamp(workflow.lastFailureAt)}
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <div className="text-xs truncate" title={workflow.lastFailureError || 'No error details'}>
                          {truncateError(workflow.lastFailureError)}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        {workflow.lastFailureNode || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {analyticsData?.items?.length === pageSize && (
            <div className="flex justify-between items-center mt-4">
              <Button
                variant="outline"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">Page {currentPage}</span>
              <Button
                variant="outline"
                onClick={() => setCurrentPage((prev) => prev + 1)}
                disabled={analyticsData.items.length < pageSize}
              >
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
