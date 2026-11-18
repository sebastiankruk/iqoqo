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
/**
 * Continuous batch scan toggle and state hook for rapid shelf inventory scanning.
 *
 * @module components/scanner/batch-scan-toggle
 */
"use client";

import React, { useState, useCallback, useRef } from "react";
import { Layers, CheckCircle2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useTranslations } from "next-intl";
import { triggerSuccessHaptic, triggerScanHaptic } from "@/lib/capacitor/haptics";

/**
 * Metadata record for an item added during a continuous batch scan session.
 */
export interface BatchScannedItem {
  id?: string | number;
  isbn?: string;
  title: string;
  authors?: string[];
  timestamp: number;
}

/**
 * Options for configuring continuous batch scanning behavior.
 */
export interface UseBatchModeOptions {
  /** Cooldown in milliseconds to prevent duplicate scans of the same barcode. Defaults to 2000ms. */
  cooldownMs?: number;
  /** Optional callback invoked whenever an item is successfully added to the batch queue. */
  onItemAdded?: (item: BatchScannedItem) => void;
}

const STORAGE_KEY = "iqoqo_batch_scan_mode";
const DEFAULT_COOLDOWN_MS = 2000;

/**
 * Hook for managing continuous batch scan state, cooldown debounce, and recent scan history.
 *
 * @param {UseBatchModeOptions} [options] - Configuration options
 * @returns State and actions for continuous batch scanning
 */
export function useBatchMode(options: UseBatchModeOptions = {}) {
  const { cooldownMs = DEFAULT_COOLDOWN_MS, onItemAdded } = options;

  const [isBatchMode, setIsBatchModeState] = useState<boolean>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEY) === "true";
    }
    return false;
  });

  const [scannedQueue, setScannedQueue] = useState<BatchScannedItem[]>([]);
  const lastBarcodeRef = useRef<string | null>(null);
  const lastTimestampRef = useRef<number>(0);

  const setBatchMode = useCallback((enabled: boolean) => {
    setIsBatchModeState(enabled);
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
    }
  }, []);

  const toggleBatchMode = useCallback(() => {
    setBatchMode(!isBatchMode);
  }, [isBatchMode, setBatchMode]);

  /**
   * Checks whether the given barcode is currently in cooldown from a consecutive scan.
   *
   * @param {string} barcode - Barcode to test against cooldown
   * @returns {boolean} True if barcode is debounced/suppressed
   */
  const isCooldownActive = useCallback(
    (barcode: string): boolean => {
      const now = Date.now();
      if (lastBarcodeRef.current === barcode && now - lastTimestampRef.current < cooldownMs) {
        return true;
      }
      return false;
    },
    [cooldownMs]
  );

  /**
   * Records a successfully scanned and added item into the batch queue, triggering
   * haptic feedback and updating the cooldown timestamp.
   *
   * @param {string} barcode - Barcode of the scanned item
   * @param {object} itemMeta - Basic metadata of the added item
   */
  const recordScan = useCallback(
    (barcode: string, itemMeta: { title: string; authors?: string[]; id?: string | number }) => {
      lastBarcodeRef.current = barcode;
      lastTimestampRef.current = Date.now();

      const newItem: BatchScannedItem = {
        id: itemMeta.id,
        isbn: barcode,
        title: itemMeta.title,
        authors: itemMeta.authors,
        timestamp: Date.now(),
      };

      setScannedQueue(prev => [newItem, ...prev]);
      triggerSuccessHaptic();
      onItemAdded?.(newItem);
    },
    [onItemAdded]
  );

  const clearQueue = useCallback(() => {
    setScannedQueue([]);
    lastBarcodeRef.current = null;
    lastTimestampRef.current = 0;
  }, []);

  return {
    isBatchMode,
    setBatchMode,
    toggleBatchMode,
    scannedQueue,
    isCooldownActive,
    recordScan,
    clearQueue,
    cooldownMs,
  };
}

/**
 * Props for the BatchScanToggle component.
 */
export interface BatchScanToggleProps {
  /** Whether continuous batch scanning is currently enabled. */
  enabled: boolean;
  /** Callback invoked when the batch mode is toggled on or off. */
  onToggle: (enabled: boolean) => void;
  /** Total count of items added during the active batch session. */
  queueCount?: number;
  /** List of recent items scanned in this batch session. */
  recentItems?: BatchScannedItem[];
  /** Callback to clear the session batch queue. */
  onClearQueue?: () => void;
  /** Optional custom CSS classes. */
  className?: string;
}

/**
 * Visual control for toggling continuous batch scanning mode on /scan.
 *
 * @param {BatchScanToggleProps} props - Component props
 * @returns {JSX.Element} The rendered toggle control
 */
export function BatchScanToggle({
  enabled,
  onToggle,
  queueCount = 0,
  recentItems = [],
  onClearQueue,
  className = "",
}: BatchScanToggleProps) {
  const t = useTranslations("scanner");

  const handleToggleClick = () => {
    triggerScanHaptic();
    onToggle(!enabled);
  };

  return (
    <div className={`flex items-center space-x-1.5 shrink-0 ${className}`}>
      <Button
        type="button"
        variant={enabled ? "default" : "outline"}
        size="sm"
        onClick={handleToggleClick}
        aria-pressed={enabled}
        className={`h-9 px-3 text-xs font-medium rounded-xl border border-border/40 shadow-sm transition-all whitespace-nowrap ${
          enabled
            ? "bg-primary text-primary-foreground shadow-sm"
            : "bg-background/80 backdrop-blur-sm text-muted-foreground hover:text-foreground"
        }`}
      >
        <Layers className={`h-4 w-4 mr-1.5 shrink-0 ${enabled ? "animate-pulse" : ""}`} />
        <span className="whitespace-nowrap">{t("batchMode.toggleLabel")}</span>
        <span
          data-testid="batch-scan-state-badge"
          className={`ml-1.5 rounded px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            enabled ? "bg-primary-foreground/20 text-primary-foreground" : "bg-muted text-muted-foreground"
          }`}
        >
          {enabled ? t("batchMode.stateOn") : t("batchMode.stateOff")}
        </span>
        {queueCount > 0 && (
          <Badge
            variant={enabled ? "secondary" : "default"}
            className="ml-1.5 px-1.5 py-0 h-4 text-[10px] font-semibold shrink-0"
          >
            {queueCount}
          </Badge>
        )}
      </Button>
      <span className="sr-only" role="status" aria-live="polite" data-testid="batch-scan-live-status">
        {enabled ? t("batchMode.statusOn") : t("batchMode.statusOff")}
      </span>

      {queueCount > 0 && recentItems.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl border border-border/40 text-muted-foreground hover:text-foreground bg-background/60 backdrop-blur-sm"
              aria-label={t("batchMode.viewQueue")}
            >
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-72 p-3 text-xs shadow-lg" align="end">
            <div className="flex items-center justify-between pb-2 border-b border-border/60">
              <span className="font-semibold text-foreground">{t("batchMode.recentScans", { count: queueCount })}</span>
              {onClearQueue && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClearQueue}
                  className="h-6 px-1.5 text-[10px] text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  {t("batchMode.clearQueue")}
                </Button>
              )}
            </div>
            <ul className="mt-2 max-h-48 overflow-y-auto space-y-1.5">
              {recentItems.slice(0, 10).map((item, index) => (
                <li
                  key={`${item.isbn || item.id}-${item.timestamp}-${index}`}
                  className="flex flex-col py-1 border-b border-border/30 last:border-none"
                >
                  <span className="font-medium text-foreground truncate">{item.title}</span>
                  {item.authors && item.authors.length > 0 && (
                    <span className="text-[11px] text-muted-foreground truncate">{item.authors.join(", ")}</span>
                  )}
                </li>
              ))}
            </ul>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
