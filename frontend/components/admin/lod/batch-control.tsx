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

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Play, SlidersHorizontal, Loader2, XCircle, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import type { LODReconciliationTaskStatus } from "@/types/admin";

export interface BatchControlProps {
  status?: LODReconciliationTaskStatus;
  isTriggering?: boolean;
  onTrigger: (params: { unlinked_only: boolean; throttle_delay: number }) => void;
  onCancel?: () => void;
  onDryRunCleanup?: () => void;
  isCleaningUp?: boolean;
}

/**
 * Batch reconciliation control panel.
 *
 * Strictly adheres to the UX auditor <= 4 buttons heuristic:
 * 1. Primary CTA: "Start Full Scan" / "Reconciling..."
 * 2. Secondary Action: "Cancel Scan" (visible only during active job execution) OR "Dry-run cleanup"
 * 3. Tertiary Action: "Scan Options" Dropdown
 *
 * @param props - Component properties containing task status and trigger callbacks.
 * @returns React component with batch execution controls and live progress tracking.
 */
export function BatchControl({
  status,
  isTriggering = false,
  onTrigger,
  onCancel,
  onDryRunCleanup,
  isCleaningUp = false,
}: BatchControlProps) {
  const t = useTranslations("LodReconciliation.batchControl");

  const [unlinkedOnly, setUnlinkedOnly] = useState(true);
  const [throttleDelay, setThrottleDelay] = useState<number>(0.5);

  const isRunning = isTriggering || status?.status === "pending" || status?.status === "processing";
  const percentage = Math.min(100, Math.max(0, status?.percentage ?? 0));

  const handleStart = () => {
    onTrigger({
      unlinked_only: unlinkedOnly,
      throttle_delay: throttleDelay,
    });
  };

  return (
    <Card data-testid="lod-batch-control-card" className="border-border/60 shadow-sm">
      <CardHeader className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4">
        <div>
          <CardTitle className="text-lg font-semibold">{t("title")}</CardTitle>
          <CardDescription className="text-sm text-muted-foreground mt-0.5">{t("description")}</CardDescription>
        </div>

        {/* Action Controls - Strictly <= 3 buttons to stay well within <= 4 button UX bound */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Button 1: Primary CTA */}
          <Button
            data-testid="lod-start-scan-button"
            onClick={handleStart}
            disabled={isRunning || isCleaningUp}
            className="gap-2 min-w-[140px]"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{t("statusProcessing")}</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>{unlinkedOnly ? t("scanUnlinked") : t("startScan")}</span>
              </>
            )}
          </Button>

          {/* Button 2: Cancel (during active run) or Dry-run cleanup (when idle) */}
          {isRunning && onCancel ? (
            <Button
              data-testid="lod-cancel-scan-button"
              variant="outline"
              onClick={onCancel}
              className="gap-2 text-destructive hover:bg-destructive/10 border-destructive/30"
            >
              <XCircle className="h-4 w-4" />
              <span>{t("cancelScan")}</span>
            </Button>
          ) : (
            onDryRunCleanup && (
              <Button
                data-testid="lod-dry-run-cleanup-button"
                variant="outline"
                onClick={onDryRunCleanup}
                disabled={isRunning || isCleaningUp}
                className="gap-2"
              >
                {isCleaningUp ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <SlidersHorizontal className="h-4 w-4" />
                )}
                <span>Dry-run cleanup</span>
              </Button>
            )
          )}

          {/* Button 3: Tertiary Options Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button data-testid="lod-scan-options-button" variant="outline" disabled={isRunning} className="gap-2">
                <SlidersHorizontal className="h-4 w-4" />
                <span>{t("options")}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>{t("options")}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                data-testid="lod-option-unlinked-only"
                checked={unlinkedOnly}
                onCheckedChange={checked => setUnlinkedOnly(Boolean(checked))}
              >
                {t("unlinkedOnly")}
              </DropdownMenuCheckboxItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>{t("throttle")}</DropdownMenuLabel>
              <DropdownMenuRadioGroup
                value={throttleDelay.toString()}
                onValueChange={v => setThrottleDelay(parseFloat(v))}
              >
                <DropdownMenuRadioItem value="0.2">{t("throttleFast")}</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="0.5">{t("throttleNormal")}</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="1.0">{t("throttleGentle")}</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      {/* Progress & Status Section */}
      {(status || isRunning) && (
        <CardContent className="pt-2 border-t border-border/40">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {status?.status === "processing" && (
                  <Badge variant="default" className="bg-blue-600 hover:bg-blue-600 gap-1 text-xs">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>{t("statusProcessing")}</span>
                  </Badge>
                )}
                {status?.status === "pending" && (
                  <Badge variant="secondary" className="gap-1 text-xs">
                    <span>{t("statusPending")}</span>
                  </Badge>
                )}
                {status?.status === "completed" && (
                  <Badge variant="default" className="bg-emerald-600 hover:bg-emerald-600 gap-1 text-xs">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>{t("statusCompleted")}</span>
                  </Badge>
                )}
                {status?.status === "failed" && (
                  <Badge variant="destructive" className="gap-1 text-xs">
                    <AlertCircle className="h-3 w-3" />
                    <span>{t("statusFailed")}</span>
                  </Badge>
                )}

                {status?.error && <span className="text-xs text-destructive truncate max-w-md">{status.error}</span>}
              </div>

              {status && (
                <span className="text-xs font-medium text-muted-foreground" data-testid="lod-progress-text">
                  {t("progressLabel", {
                    processed: status.processed ?? 0,
                    total: status.total ?? 0,
                    percent: Math.round(percentage),
                  })}
                </span>
              )}
            </div>

            {/* Visual Progress Bar */}
            <div
              data-testid="lod-progress-bar-container"
              className="h-2.5 w-full rounded-full bg-secondary overflow-hidden"
            >
              <div
                data-testid="lod-progress-bar-indicator"
                className={`h-full transition-all duration-300 ${
                  status?.status === "failed"
                    ? "bg-destructive"
                    : status?.status === "completed"
                      ? "bg-emerald-600"
                      : "bg-primary"
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
