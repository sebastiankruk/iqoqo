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

import { useState, useEffect, useCallback } from "react";
import {
  getOwnershipAccounts,
  getOwnershipItems,
  previewOwnershipReassignment,
  executeOwnershipReassignment,
  OwnershipAccount,
  OwnershipSourceItem,
  OwnershipPreviewResponse,
} from "@/lib/api/admin";
import { Loader2, AlertCircle, ArrowRight, ShieldAlert, Lock, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

/**
 * Component for admin item ownership reassignment.
 *
 * Implements source & target account selection, paginated item browsing with
 * single/multi-select, all-items source scope, atomic server preview, affirmative
 * all-scope acknowledgement, and conflict handling.
 */
export function OwnershipManagement() {
  const [accounts, setAccounts] = useState<OwnershipAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [sourceUserId, setSourceUserId] = useState<string>("");
  const [targetUserId, setTargetUserId] = useState<string>("");

  // Items state
  const [items, setItems] = useState<OwnershipSourceItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setPages] = useState(1);
  const [loadingItems, setLoadingItems] = useState(false);
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);

  // Dialog and Preview state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<OwnershipPreviewResponse | null>(null);
  const [executing, setExecuting] = useState(false);
  const [allScopeAcknowledged, setAllScopeAcknowledged] = useState(false);

  // Load accounts on mount
  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    try {
      const data = await getOwnershipAccounts();
      setAccounts(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load accounts";
      toast.error(msg);
    } finally {
      setLoadingAccounts(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchAccounts();
  }, [fetchAccounts]);

  // Load items when sourceUserId or page changes
  const fetchItems = useCallback(async () => {
    if (!sourceUserId) {
      setItems([]);
      setTotalItems(0);
      setPages(1);
      setSelectedItemIds([]);
      return;
    }
    setLoadingItems(true);
    try {
      const res = await getOwnershipItems(sourceUserId, page, 20);
      setItems(res.items);
      setTotalItems(res.total);
      setPages(res.pages);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load items";
      toast.error(msg);
    } finally {
      setLoadingItems(false);
    }
  }, [sourceUserId, page]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchItems();
  }, [fetchItems]);

  const handleSourceChange = (newSourceId: string) => {
    setSourceUserId(newSourceId);
    setPage(1);
    setSelectedItemIds([]);
    if (targetUserId === newSourceId) {
      setTargetUserId("");
    }
  };

  const toggleItemSelection = (id: number) => {
    setSelectedItemIds(prev => (prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]));
  };

  const selectAllPageItems = () => {
    const pageIds = items.map(i => i.id);
    const allSelected = pageIds.every(id => selectedItemIds.includes(id));
    if (allSelected) {
      setSelectedItemIds(prev => prev.filter(id => !pageIds.includes(id)));
    } else {
      setSelectedItemIds(prev => Array.from(new Set([...prev, ...pageIds])));
    }
  };

  // Open Preview Dialog
  const handleOpenPreview = async (mode: "single" | "selected" | "all", singleItemId?: number) => {
    if (!sourceUserId || !targetUserId) {
      toast.error("Please select both source and target accounts");
      return;
    }
    if (sourceUserId === targetUserId) {
      toast.error("Source and target accounts must be distinct");
      return;
    }

    const itemIds =
      mode === "single" ? (singleItemId ? [singleItemId] : []) : mode === "selected" ? selectedItemIds : undefined;

    if (mode === "selected" && (!itemIds || itemIds.length === 0)) {
      toast.error("Please select at least one item to reassign");
      return;
    }

    setPreviewLoading(true);
    setPreviewData(null);
    setAllScopeAcknowledged(false);
    setPreviewOpen(true);

    try {
      const preview = await previewOwnershipReassignment({
        source_user_id: sourceUserId,
        target_user_id: targetUserId,
        mode,
        item_ids: itemIds,
      });
      setPreviewData(preview);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Preview calculation failed";
      toast.error(msg);
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Execute Reassignment
  const handleConfirmReassignment = async () => {
    if (!previewData) return;

    if (previewData.mode === "all" && !allScopeAcknowledged) {
      toast.error("Please explicitly acknowledge all-items reassignment");
      return;
    }

    setExecuting(true);
    try {
      const res = await executeOwnershipReassignment({
        source_user_id: previewData.source.id,
        target_user_id: previewData.target.id,
        mode: previewData.mode,
        expected_fingerprint: previewData.fingerprint,
        expected_count: previewData.total_count,
        item_ids: previewData.mode !== "all" ? previewData.item_ids : undefined,
      });

      toast.success(
        `Successfully transferred ${res.transferred_count} physical item(s) to ${previewData.target.display_name || previewData.target.username}`
      );
      setPreviewOpen(false);
      setSelectedItemIds([]);
      // Refresh items list
      fetchItems();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Reassignment failed";
      toast.error(msg);
      // If conflict or stale, close dialog so admin re-previews
      setPreviewOpen(false);
    } finally {
      setExecuting(false);
    }
  };

  const isAllPageSelected = items.length > 0 && items.every(i => selectedItemIds.includes(i.id));

  return (
    <div className="space-y-6">
      {/* Account Selection Card */}
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight mb-4">Account Selection</h2>
        {loadingAccounts ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading user accounts...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Source Account */}
            <div className="space-y-2">
              <label htmlFor="source-account-select" className="text-sm font-medium text-foreground">
                Source Account (Current Owner)
              </label>
              <select
                id="source-account-select"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
                value={sourceUserId}
                onChange={e => handleSourceChange(e.target.value)}
              >
                <option value="">Select source account...</option>
                {accounts.map(acc => (
                  <option key={acc.id} value={acc.id}>
                    {acc.display_name || acc.username || acc.email} ({acc.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Target Account */}
            <div className="space-y-2">
              <label htmlFor="target-account-select" className="text-sm font-medium text-foreground">
                Target Account (New Owner)
              </label>
              <select
                id="target-account-select"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
                value={targetUserId}
                onChange={e => setTargetUserId(e.target.value)}
              >
                <option value="">Select target account...</option>
                {accounts
                  .filter(acc => acc.id !== sourceUserId && acc.is_active)
                  .map(acc => (
                    <option key={acc.id} value={acc.id}>
                      {acc.display_name || acc.username || acc.email} ({acc.email})
                    </option>
                  ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Items List & Actions Card */}
      {sourceUserId && (
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-4">
            <div>
              <h3 className="text-base font-semibold">Source Items ({totalItems} total)</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Physical items owned by the source account.</p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleOpenPreview("selected")}
                disabled={selectedItemIds.length === 0 || !targetUserId}
              >
                Transfer Selected ({selectedItemIds.length})
              </Button>

              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleOpenPreview("all")}
                disabled={totalItems === 0 || !targetUserId}
              >
                Transfer All Source Items ({totalItems})
              </Button>
            </div>
          </div>

          {/* Items Table */}
          {loadingItems ? (
            <div className="flex justify-center items-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-12 text-sm text-muted-foreground">
              No physical items found for this user.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="py-2 px-3 w-10">
                      <input
                        type="checkbox"
                        aria-label="Select all items on this page"
                        checked={isAllPageSelected}
                        onChange={selectAllPageItems}
                        className="rounded border-input text-primary focus:ring-primary h-4 w-4"
                      />
                    </th>
                    <th className="py-2 px-3">ID</th>
                    <th className="py-2 px-3">Title</th>
                    <th className="py-2 px-3">Format</th>
                    <th className="py-2 px-3">Visibility</th>
                    <th className="py-2 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map(item => {
                    const isSelected = selectedItemIds.includes(item.id);
                    return (
                      <tr
                        key={item.id}
                        className={isSelected ? "bg-muted/50 transition-colors" : "hover:bg-muted/30 transition-colors"}
                      >
                        <td className="py-3 px-3">
                          <input
                            type="checkbox"
                            aria-label={`Select item ${item.id}`}
                            checked={isSelected}
                            onChange={() => toggleItemSelection(item.id)}
                            className="rounded border-input text-primary focus:ring-primary h-4 w-4"
                          />
                        </td>
                        <td className="py-3 px-3 font-mono text-xs text-muted-foreground">#{item.id}</td>
                        <td className="py-3 px-3 font-medium">{item.title}</td>
                        <td className="py-3 px-3 text-muted-foreground text-xs">{item.format || "N/A"}</td>
                        <td className="py-3 px-3">
                          {item.is_hidden ? (
                            <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-500">
                              <Lock className="h-3 w-3" />
                              Hidden
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500">
                              Visible
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={!targetUserId}
                            onClick={() => handleOpenPreview("single", item.id)}
                          >
                            Transfer <ArrowRight className="ml-1 h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t pt-4 mt-4 text-xs text-muted-foreground">
                  <div>
                    Page {page} of {totalPages}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(p - 1, 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.min(p + 1, totalPages))}
                      disabled={page === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Reassignment Preview & Confirmation Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              Confirm Ownership Reassignment
            </DialogTitle>
            <DialogDescription>
              Review the provenance impact and access boundary changes before executing this atomic transfer.
            </DialogDescription>
          </DialogHeader>

          {previewLoading ? (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
              Calculating transfer digest and locking parameters...
            </div>
          ) : !previewData || previewData.total_count === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
              No items match the requested transfer criteria.
            </div>
          ) : (
            <div className="space-y-4 py-2 text-sm">
              {/* Transfer Details Card */}
              <div className="rounded-md border bg-muted/40 p-3 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted-foreground font-medium">Source Account:</span>
                  <span className="font-semibold text-foreground">
                    {previewData.source.display_name || previewData.source.username}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted-foreground font-medium">Target Account:</span>
                  <span className="font-semibold text-foreground">
                    {previewData.target.display_name || previewData.target.username}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted-foreground font-medium">Operation Scope:</span>
                  <span className="uppercase font-mono text-xs font-semibold text-primary">
                    {previewData.mode} ({previewData.total_count} item{previewData.total_count > 1 ? "s" : ""})
                  </span>
                </div>
              </div>

              {/* Composition Breakdown */}
              <div className="rounded-md border p-3 space-y-2">
                <div className="text-xs font-semibold text-foreground">Item Composition Breakdown</div>
                <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-4">
                  <li>
                    Total physical items to transfer: <strong>{previewData.total_count}</strong>
                  </li>
                  {previewData.hidden_count > 0 && (
                    <li>
                      Hidden items included: <strong>{previewData.hidden_count}</strong> (remain hidden, private to
                      target)
                    </li>
                  )}
                  {previewData.lent_count > 0 && (
                    <li>
                      Active loans included: <strong>{previewData.lent_count}</strong> (loan records preserved, target
                      becomes owner)
                    </li>
                  )}
                </ul>
              </div>

              {/* Access Consequences Warning */}
              <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400 space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4" />
                  Access & Visibility Boundaries:
                </div>
                <p>• Target account gains full owner-scoped access; source account loses ownership access.</p>
                <p>• Non-hidden items become visible under target account&apos;s profile/shared catalog.</p>
                <p>• Items are atomically removed from any of source account&apos;s personal collections.</p>
              </div>

              {/* All-Scope Affirmative Checkbox */}
              {previewData.mode === "all" && (
                <div className="flex items-start gap-2 pt-2 border-t">
                  <input
                    type="checkbox"
                    id="all-scope-acknowledgement"
                    checked={allScopeAcknowledged}
                    onChange={e => setAllScopeAcknowledged(e.target.checked)}
                    className="mt-1 rounded border-input text-primary focus:ring-primary h-4 w-4"
                  />
                  <label
                    htmlFor="all-scope-acknowledgement"
                    className="text-xs font-medium text-foreground leading-snug cursor-pointer select-none"
                  >
                    I explicitly confirm reassigning <strong>ALL {previewData.total_count}</strong> physical items from{" "}
                    {previewData.source.display_name || previewData.source.username} to{" "}
                    {previewData.target.display_name || previewData.target.username}.
                  </label>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setPreviewOpen(false)} disabled={executing}>
              Cancel
            </Button>
            {previewData && previewData.total_count > 0 && (
              <Button
                variant="destructive"
                onClick={handleConfirmReassignment}
                disabled={executing || previewLoading || (previewData.mode === "all" && !allScopeAcknowledged)}
              >
                {executing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Reassigning...
                  </>
                ) : (
                  "Confirm Reassignment"
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
