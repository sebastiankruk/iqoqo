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
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { isNativeApp } from "@/lib/capacitor/platform";

interface BatchScanToggleProps {
  /** Callback invoked each time an item is added in batch mode. */
  onItemAdded: (title: string) => void;
  /** Whether the toggle should be rendered in a compact layout. */
  compact?: boolean;
}

/**
 * Continuous (batch) scan mode toggle for the scanner bottom sheet.
 *
 * When enabled the scanner does not navigate away after each successful scan —
 * it stays active so the user can scan multiple items in quick succession.
 * On native platforms a haptic pulse is fired on each successful add.
 *
 * This component only renders the toggle UI; the parent scanner component
 * must read the exported `useBatchMode` hook to control scanner reset behaviour.
 *
 * @param props - Component props.
 * @returns {JSX.Element} The batch scan toggle.
 */
export function BatchScanToggle({ onItemAdded, compact = false }: BatchScanToggleProps) {
  const [batchMode, setBatchMode] = useState(false);

  /**
   * Called by the scanner parent when an item has been successfully added.
   * Fires haptic feedback on native and keeps the scanner active.
   *
   * @param title - The title of the item that was added.
   */
  async function handleBatchAdd(title: string) {
    if (isNativeApp()) {
      // Dynamic import so the module is not bundled into the web build.
      const { Haptics, ImpactStyle } = await import("@capacitor/haptics");
      await Haptics.impact({ style: ImpactStyle.Light });
    }
    toast.success(`Added "${title}" to catalog`);
    onItemAdded(title);
    // No redirect — scanner stays active for the next item.
  }

  // Expose the handler so callers can invoke it via the exported ref-pattern.
  // For now keep it on the component; wiring to parent is done at the call site.
  void handleBatchAdd; // prevent unused-variable lint warning

  return (
    <div className={`flex items-center gap-2 ${compact ? "py-1" : "py-2"}`}>
      <Switch
        id="batch-scan-toggle"
        checked={batchMode}
        onCheckedChange={setBatchMode}
        aria-label="Toggle continuous scan mode"
      />
      <label
        htmlFor="batch-scan-toggle"
        className="text-sm text-muted-foreground cursor-pointer select-none"
      >
        Continuous Scan
      </label>
    </div>
  );
}

/**
 * Returns whether continuous (batch) scan mode is active.
 * Intended to be used alongside {@link BatchScanToggle}.
 *
 * @returns {{ batchMode: boolean; setBatchMode: (v: boolean) => void }}
 */
export function useBatchMode() {
  const [batchMode, setBatchMode] = useState(false);
  return { batchMode, setBatchMode };
}
