// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ChevronRight, Home, Loader2, RefreshCw, Network } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { Button } from "@/components/ui/button";
import { useProfile } from "@/lib/api/hooks";
import {
  useLodStats,
  useLodTaskStatus,
  useTriggerLodReconciliation,
  useTriggerLodCleanup,
  useActiveLodTask,
  useCancelLodTask,
} from "@/lib/api/hooks/admin";
import { PermissionName } from "@/lib/permissions";
import { MetricCards } from "@/components/admin/lod/metric-cards";
import { BatchControl } from "@/components/admin/lod/batch-control";
import { AuditLogStream } from "@/components/admin/lod/audit-log-stream";
import { toast } from "sonner";

/**
 * Administrative and Custodian LOD Reconciliation Dashboard.
 *
 * Provides batch entity linking controls across external knowledge graphs
 * (DBpedia, GeoNames, WordNet), real-time progress tracking, and resolution audit stream.
 *
 * @returns React component representing the full dashboard page.
 */
export default function LodReconciliationPage() {
  const t = useTranslations("LodReconciliation");
  const { data: profile, isLoading: isProfileLoading } = useProfile();

  const { data: activeTaskData } = useActiveLodTask();
  const [activeTaskId, setActiveTaskId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      try {
        return localStorage.getItem("iqoqo_active_lod_task_id");
      } catch {
        return null;
      }
    }
    return null;
  });

  // The server is authoritative about which task is running, so its answer is
  // merged during render rather than copied into state from an effect. Writing
  // it in an effect is a second render pass that briefly shows a stale id, and
  // `set-state-in-effect` exists to flag exactly that. The localStorage write
  // is a genuine side effect, so it stays in an effect -- but it now only
  // mirrors the id, and it no longer drives what the page displays.
  const serverActiveTaskId = activeTaskData?.active_task_id ?? null;
  const effectiveActiveTaskId = activeTaskId ?? serverActiveTaskId;

  useEffect(() => {
    if (serverActiveTaskId) {
      try {
        localStorage.setItem("iqoqo_active_lod_task_id", serverActiveTaskId);
      } catch {
        // ignore
      }
    }
  }, [serverActiveTaskId]);

  const { data: stats, isLoading: isStatsLoading, isFetching: isFetchingStats, refetch: refetchStats } = useLodStats();
  const { data: taskStatus } = useLodTaskStatus(effectiveActiveTaskId);
  const triggerMutation = useTriggerLodReconciliation();
  const cancelMutation = useCancelLodTask();
  const cleanupMutation = useTriggerLodCleanup();

  // If activeTaskData has task snapshot from /active endpoint, use it before or alongside taskStatus
  const effectiveTaskStatus = taskStatus ?? activeTaskData?.task ?? undefined;

  const roles = profile?.roles ?? [];
  const permissions = profile?.permissions ?? [];

  const canAccess =
    roles.includes("admin") ||
    roles.includes("custodian") ||
    permissions.includes(PermissionName.REFETCH_METADATA) ||
    permissions.includes(PermissionName.WRITE_METADATA);

  // Monitor task completion to refresh catalog statistics and clean active storage
  useEffect(() => {
    if (taskStatus?.status === "completed" || taskStatus?.status === "cancelled") {
      refetchStats();
      try {
        localStorage.removeItem("iqoqo_active_lod_task_id");
      } catch {
        // ignore
      }
    } else if (taskStatus?.status === "failed") {
      try {
        localStorage.removeItem("iqoqo_active_lod_task_id");
      } catch {
        // ignore
      }
    }
  }, [taskStatus?.status, refetchStats]);

  const handleRefreshStats = async () => {
    await refetchStats();
    toast.success("Stats refreshed");
  };

  const handleTrigger = async (params: { unlinked_only: boolean; throttle_delay: number }) => {
    try {
      const result = await triggerMutation.mutateAsync({
        unlinked_only: params.unlinked_only,
        throttle_delay: params.throttle_delay,
      });

      if (result?.task_id) {
        setActiveTaskId(result.task_id);
        try {
          localStorage.setItem("iqoqo_active_lod_task_id", result.task_id);
        } catch {
          // ignore
        }
        toast.success(result.message || t("batchControl.statusPending"));
      }
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { status?: number; data?: { error?: string; data?: { active_task_id?: string } } };
        message?: string;
      };
      if (axiosErr.response?.status === 409) {
        const runningId = axiosErr.response.data?.data?.active_task_id;
        if (runningId) {
          setActiveTaskId(runningId);
          try {
            localStorage.setItem("iqoqo_active_lod_task_id", runningId);
          } catch {
            // ignore
          }
        }
        toast.warning(axiosErr.response.data?.error || "A reconciliation scan is already running");
        return;
      }
      const msg = err instanceof Error ? err.message : "Failed to dispatch reconciliation task";
      toast.error(msg);
    }
  };

  const handleCancel = async () => {
    const taskToCancel = effectiveActiveTaskId;
    setActiveTaskId(null);
    try {
      localStorage.removeItem("iqoqo_active_lod_task_id");
    } catch {
      // ignore
    }
    try {
      await cancelMutation.mutateAsync(taskToCancel);
      toast.info(t("batchControl.cancelScan"));
      await refetchStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel scan";
      toast.error(msg);
    }
  };

  const handleDryRunCleanup = async () => {
    try {
      const result = await cleanupMutation.mutateAsync(true);
      toast.info(`Dry-run cleanup complete: ${result.demoted} candidate links identified for demotion.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run LOD cleanup dry-run";
      toast.error(msg);
    }
  };

  if (isProfileLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!canAccess) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4">
          <div className="h-12 w-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
            <Network className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{t("accessDenied")}</h1>
          <p className="text-muted-foreground max-w-md text-sm">{t("accessDeniedDesc")}</p>
          <Button asChild>
            <Link href="/dashboard">{t("backToDashboard")}</Link>
          </Button>
        </main>
        <Footer />
      </div>
    );
  }

  const isProcessing = effectiveTaskStatus?.status === "processing" || effectiveTaskStatus?.status === "pending";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Breadcrumb Navigation */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/" className="hover:text-foreground transition-colors flex items-center gap-1">
            <Home className="h-3.5 w-3.5" />
            <span>Home</span>
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <Link href="/admin/content" className="hover:text-foreground transition-colors">
            Custodians
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="font-medium text-foreground">{t("breadcrumb")}</span>
        </nav>

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Network className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{t("title")}</h1>
            </div>
            <p className="text-sm text-muted-foreground">{t("description")}</p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshStats}
              disabled={isStatsLoading || isFetchingStats}
              className="gap-2 h-9 text-xs"
              title="Refresh statistics"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetchingStats ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh stats</span>
            </Button>

            <Button variant="outline" size="sm" asChild className="h-9 text-xs">
              <Link href="/admin/content">Custodian Content</Link>
            </Button>

            <Button variant="outline" size="sm" asChild className="h-9 text-xs">
              <Link href="/admin/sparql">SPARQL</Link>
            </Button>
          </div>
        </div>

        {/* 1. Summary Metrics */}
        <section aria-label="Authority Metrics">
          <MetricCards
            stats={stats}
            taskCounts={effectiveTaskStatus?.counts}
            totalProcessed={effectiveTaskStatus?.processed}
            isProcessing={isProcessing}
          />
        </section>

        {/* 2. Batch Execution Control & Progress Bar */}
        <section aria-label="Batch Control">
          <BatchControl
            status={effectiveTaskStatus}
            isTriggering={triggerMutation.isPending}
            onTrigger={handleTrigger}
            onCancel={handleCancel}
            onDryRunCleanup={handleDryRunCleanup}
            isCleaningUp={cleanupMutation.isPending}
          />
        </section>

        {/* 3. Live Item Resolution Audit Log Stream */}
        <section aria-label="Resolution Audit Stream">
          <AuditLogStream logs={effectiveTaskStatus?.recent_logs ?? []} isLoading={isProcessing} />
        </section>
      </main>

      <Footer />
    </div>
  );
}
