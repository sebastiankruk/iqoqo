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

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MetricCards } from "@/components/admin/lod/metric-cards";
import { BatchControl } from "@/components/admin/lod/batch-control";
import { AuditLogStream } from "@/components/admin/lod/audit-log-stream";
import LodReconciliationPage from "@/app/admin/lod/page";
import * as hooks from "@/lib/api/hooks";
import * as adminHooks from "@/lib/api/hooks/admin";
import type { LODStats, LODReconciliationTaskStatus, LODLogEntry } from "@/types/admin";

// Mock next-intl translations
vi.mock("next-intl", () => ({
  useTranslations: (ns: string) => {
    return (key: string, params?: Record<string, unknown>) => {
      const fullKey = `${ns}.${key}`;
      const translations: Record<string, string> = {
        "LodReconciliation.title": "LOD reconciliation",
        "LodReconciliation.description": "Trigger catalog-wide entity linking",
        "LodReconciliation.breadcrumb": "LOD reconciliation",
        "LodReconciliation.accessDenied": "Access denied",
        "LodReconciliation.accessDeniedDesc": "You need administrative or custodian permissions",
        "LodReconciliation.backToDashboard": "Back to dashboard",
        "LodReconciliation.metrics.totalManifestations": "Total editions",
        "LodReconciliation.metrics.linkedManifestations": "Linked editions",
        "LodReconciliation.metrics.unlinkedManifestations": "Unlinked editions",
        "LodReconciliation.metrics.totalLinks": "Total semantic links",
        "LodReconciliation.metrics.dbpediaLinks": "DBpedia links",
        "LodReconciliation.metrics.geonamesLinks": "GeoNames links",
        "LodReconciliation.metrics.wordnetLinks": "WordNet links",
        "LodReconciliation.batchControl.title": "Batch reconciliation control",
        "LodReconciliation.batchControl.description": "Launch asynchronous catalog reconciliation",
        "LodReconciliation.batchControl.startScan": "Start full scan",
        "LodReconciliation.batchControl.scanUnlinked": "Scan unlinked only",
        "LodReconciliation.batchControl.options": "Scan options",
        "LodReconciliation.batchControl.unlinkedOnly": "Unlinked entities only",
        "LodReconciliation.batchControl.allEntities": "All entities",
        "LodReconciliation.batchControl.throttle": "Throttle delay",
        "LodReconciliation.batchControl.throttleFast": "Fast (0.2s)",
        "LodReconciliation.batchControl.throttleNormal": "Normal (0.5s)",
        "LodReconciliation.batchControl.throttleGentle": "Gentle (1.0s)",
        "LodReconciliation.batchControl.cancelScan": "Cancel scan",
        "LodReconciliation.batchControl.statusPending": "Queued",
        "LodReconciliation.batchControl.statusProcessing": "Reconciling catalog...",
        "LodReconciliation.batchControl.statusCompleted": "Reconciliation complete",
        "LodReconciliation.batchControl.statusFailed": "Reconciliation failed",
        "LodReconciliation.auditLog.title": "Resolution audit stream",
        "LodReconciliation.auditLog.description": "Live feed of recent item-by-item events",
        "LodReconciliation.auditLog.filterAll": "All outcomes",
        "LodReconciliation.auditLog.filterSuccess": "Success only",
        "LodReconciliation.auditLog.filterSkipped": "Skipped only",
        "LodReconciliation.auditLog.filterWarn": "Warnings & errors",
        "LodReconciliation.auditLog.autoScroll": "Auto-scroll",
        "LodReconciliation.auditLog.noLogs": "No resolution events yet",
        "LodReconciliation.auditLog.noLinksAdded": "No links matched",
      };

      if (key === "progressLabel" && params) {
        return `${params.processed} of ${params.total} editions (${params.percent}%)`;
      }
      if (key === "linksAdded" && params) {
        return `${params.count} links added`;
      }

      return translations[fullKey] || key;
    };
  },
}));

// Mock hooks
vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/hooks/admin", () => ({
  useLodStats: vi.fn(),
  useLodTaskStatus: vi.fn(),
  useTriggerLodReconciliation: vi.fn(),
  useActiveLodTask: vi.fn(),
  useCancelLodTask: vi.fn().mockReturnValue({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <div data-testid="mock-navbar">Navbar</div>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <div data-testid="mock-footer">Footer</div>,
}));

describe("LOD Reconciliation Dashboard Component Suite", () => {
  const sampleStats: LODStats = {
    total_manifestations: 150,
    linked_manifestations: 120,
    unlinked_manifestations: 30,
    total_links: 310,
    by_authority: {
      dbpedia: 140,
      geonames: 95,
      wordnet: 75,
    },
  };

  const sampleLogs: LODLogEntry[] = [
    {
      timestamp: "2026-09-27T10:00:00Z",
      manifestation_id: 1,
      title: "The Fellowship of the Ring",
      status: "SUCCESS",
      links_added: 3,
      authorities: ["dbpedia", "geonames", "wordnet"],
      error: null,
    },
    {
      timestamp: "2026-09-27T10:00:01Z",
      manifestation_id: 2,
      title: "Obscure Indie Zine",
      status: "SKIPPED",
      links_added: 0,
      authorities: [],
      error: null,
    },
    {
      timestamp: "2026-09-27T10:00:02Z",
      manifestation_id: 3,
      title: "Corrupted Record",
      status: "WARN",
      links_added: 0,
      authorities: [],
      error: "Rate limit reached",
    },
  ];

  const sampleTaskStatus: LODReconciliationTaskStatus = {
    task_id: "test-task-123",
    status: "processing",
    state: "PROGRESS",
    percentage: 65.5,
    total: 100,
    processed: 65,
    total_resolved: 45,
    counts: {
      dbpedia: 20,
      geonames: 15,
      wordnet: 10,
    },
    recent_logs: sampleLogs,
    error: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminHooks.useActiveLodTask).mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof adminHooks.useActiveLodTask>);
  });

  describe("MetricCards", () => {
    it("renders lifetime statistics for all 4 summary cards with drill-down links", () => {
      render(<MetricCards stats={sampleStats} />);

      const manifCard = screen.getByTestId("metric-card-manifestations");
      expect(manifCard).toBeInTheDocument();
      expect(manifCard.closest("a")).toHaveAttribute("href", "/collection");
      expect(manifCard).toHaveTextContent("150");
      expect(manifCard).toHaveTextContent("120 linked · 30 unlinked");

      const dbpediaCard = screen.getByTestId("metric-card-dbpedia");
      expect(dbpediaCard).toBeInTheDocument();
      expect(dbpediaCard.closest("a")).toHaveAttribute("href", "/collection?lod_authority=dbpedia");
      expect(screen.getByText("140")).toBeInTheDocument();

      const geonamesCard = screen.getByTestId("metric-card-geonames");
      expect(geonamesCard).toBeInTheDocument();
      expect(geonamesCard.closest("a")).toHaveAttribute("href", "/collection?lod_authority=geonames");
      expect(screen.getByText("95")).toBeInTheDocument();

      const wordnetCard = screen.getByTestId("metric-card-wordnet");
      expect(wordnetCard).toBeInTheDocument();
      expect(wordnetCard.closest("a")).toHaveAttribute("href", "/collection?lod_authority=wordnet");
      expect(screen.getByText("75")).toBeInTheDocument();
    });

    it("displays active scan counts when a reconciliation task is executing", () => {
      render(
        <MetricCards stats={sampleStats} taskCounts={sampleTaskStatus.counts} totalProcessed={65} isProcessing={true} />
      );

      expect(screen.getByText("65 processed in scan")).toBeInTheDocument();
      expect(screen.getByText("+20 in active scan")).toBeInTheDocument();
      expect(screen.getByText("+15 in active scan")).toBeInTheDocument();
      expect(screen.getByText("+10 in active scan")).toBeInTheDocument();
    });
  });

  describe("BatchControl", () => {
    it("strictly adheres to the UX auditor button count bound (<= 4 buttons)", () => {
      const mockTrigger = vi.fn();
      const { container } = render(<BatchControl onTrigger={mockTrigger} isTriggering={false} />);

      const buttons = container.querySelectorAll("button");
      expect(buttons.length).toBeLessThanOrEqual(4);
    });

    it("triggers reconciliation when clicking primary CTA defaulting to unlinked_only=true", () => {
      const mockTrigger = vi.fn();
      render(<BatchControl onTrigger={mockTrigger} isTriggering={false} />);

      const startButton = screen.getByTestId("lod-start-scan-button");
      fireEvent.click(startButton);

      expect(mockTrigger).toHaveBeenCalledWith({
        unlinked_only: true,
        throttle_delay: 0.5,
      });
    });

    it("renders progress bar, percentage, and cancel button when active", () => {
      const mockTrigger = vi.fn();
      const mockCancel = vi.fn();

      render(<BatchControl status={sampleTaskStatus} onTrigger={mockTrigger} onCancel={mockCancel} />);

      expect(screen.getByTestId("lod-progress-text")).toHaveTextContent("65 of 100 editions (66%)");
      const indicator = screen.getByTestId("lod-progress-bar-indicator");
      expect(indicator).toHaveStyle({ width: "65.5%" });

      const cancelButton = screen.getByTestId("lod-cancel-scan-button");
      expect(cancelButton).toBeInTheDocument();
      fireEvent.click(cancelButton);
      expect(mockCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe("AuditLogStream", () => {
    it("renders log entries with status chips and authority tags", () => {
      render(<AuditLogStream logs={sampleLogs} />);

      const logEntries = screen.getAllByTestId("lod-log-entry");
      expect(logEntries).toHaveLength(3);

      expect(screen.getByText("SUCCESS")).toBeInTheDocument();
      expect(screen.getByText("SKIPPED")).toBeInTheDocument();
      expect(screen.getByText("WARN")).toBeInTheDocument();

      expect(screen.getByText(/The Fellowship of the Ring/)).toBeInTheDocument();
      expect(screen.getByText("DBpedia")).toBeInTheDocument();
      expect(screen.getByText("GeoNames")).toBeInTheDocument();
      expect(screen.getByText("WordNet")).toBeInTheDocument();
      expect(screen.getByText("3 links added")).toBeInTheDocument();
    });

    it("renders empty state message when no logs are available", () => {
      render(<AuditLogStream logs={[]} />);
      expect(screen.getByTestId("lod-no-logs-message")).toHaveTextContent("No resolution events yet");
    });

    it("toggles auto-scroll state with explicit high-contrast ON/OFF labels", () => {
      render(<AuditLogStream logs={sampleLogs} />);
      const autoScrollButton = screen.getByTestId("lod-autoscroll-toggle");
      expect(autoScrollButton).toBeInTheDocument();
      expect(autoScrollButton).toHaveTextContent("Auto-scroll: ON");

      fireEvent.click(autoScrollButton);
      expect(autoScrollButton).toHaveTextContent("Auto-scroll: OFF");

      fireEvent.click(autoScrollButton);
      expect(autoScrollButton).toHaveTextContent("Auto-scroll: ON");
    });
  });

  describe("LodReconciliationPage Access Control", () => {
    it("denies access to standard collectors without admin or custodian privileges", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "u-1",
          email: "collector@iqoqo.org",
          roles: ["collector"],
          permissions: ["read:metadata"],
        },
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      vi.mocked(adminHooks.useLodStats).mockReturnValue({
        data: sampleStats,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof adminHooks.useLodStats>);

      vi.mocked(adminHooks.useLodTaskStatus).mockReturnValue({
        data: undefined,
      } as unknown as ReturnType<typeof adminHooks.useLodTaskStatus>);

      vi.mocked(adminHooks.useTriggerLodReconciliation).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof adminHooks.useTriggerLodReconciliation>);

      render(<LodReconciliationPage />);

      expect(screen.getByText("Access denied")).toBeInTheDocument();
      expect(screen.getByText("Back to dashboard")).toBeInTheDocument();
    });

    it("grants access to Custodian accounts", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "u-2",
          email: "custodian@iqoqo.org",
          roles: ["custodian"],
          permissions: ["refetch:metadata"],
        },
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      vi.mocked(adminHooks.useLodStats).mockReturnValue({
        data: sampleStats,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof adminHooks.useLodStats>);

      vi.mocked(adminHooks.useLodTaskStatus).mockReturnValue({
        data: undefined,
      } as unknown as ReturnType<typeof adminHooks.useLodTaskStatus>);

      vi.mocked(adminHooks.useTriggerLodReconciliation).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof adminHooks.useTriggerLodReconciliation>);

      render(<LodReconciliationPage />);

      expect(screen.getByRole("heading", { name: "LOD reconciliation" })).toBeInTheDocument();
      expect(screen.getByTestId("lod-batch-control-card")).toBeInTheDocument();
      expect(screen.getByTestId("lod-audit-log-card")).toBeInTheDocument();
    });

    it("grants access to Administrator accounts", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "u-3",
          email: "admin@iqoqo.org",
          roles: ["admin"],
          permissions: ["config:internal"],
        },
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      vi.mocked(adminHooks.useLodStats).mockReturnValue({
        data: sampleStats,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof adminHooks.useLodStats>);

      vi.mocked(adminHooks.useLodTaskStatus).mockReturnValue({
        data: sampleTaskStatus,
      } as unknown as ReturnType<typeof adminHooks.useLodTaskStatus>);

      vi.mocked(adminHooks.useTriggerLodReconciliation).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof adminHooks.useTriggerLodReconciliation>);

      render(<LodReconciliationPage />);

      expect(screen.getByRole("heading", { name: "LOD reconciliation" })).toBeInTheDocument();
      expect(screen.getByTestId("lod-progress-text")).toBeInTheDocument();
    });

    it("automatically rehydrates and tracks in-flight task on page load", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "u-3",
          email: "admin@iqoqo.org",
          roles: ["admin"],
          permissions: ["config:internal"],
        },
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      vi.mocked(adminHooks.useActiveLodTask).mockReturnValue({
        data: {
          active_task_id: "persisted-task-456",
          status: "processing",
        },
        isLoading: false,
      } as unknown as ReturnType<typeof adminHooks.useActiveLodTask>);

      vi.mocked(adminHooks.useLodStats).mockReturnValue({
        data: sampleStats,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof adminHooks.useLodStats>);

      vi.mocked(adminHooks.useLodTaskStatus).mockImplementation((taskId: string | null) => {
        if (taskId === "persisted-task-456") {
          return { data: sampleTaskStatus } as unknown as ReturnType<typeof adminHooks.useLodTaskStatus>;
        }
        return { data: undefined } as unknown as ReturnType<typeof adminHooks.useLodTaskStatus>;
      });

      vi.mocked(adminHooks.useTriggerLodReconciliation).mockReturnValue({
        mutateAsync: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof adminHooks.useTriggerLodReconciliation>);

      render(<LodReconciliationPage />);

      expect(adminHooks.useLodTaskStatus).toHaveBeenCalledWith("persisted-task-456");
      expect(screen.getByTestId("lod-progress-text")).toBeInTheDocument();
    });
  });
});
