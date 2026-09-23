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

import { useState, useCallback, useEffect } from "react";
import { toast } from "sonner";
import { Loader2, Search, ArrowRightLeft, Merge, SplitSquareVertical } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  reassignFrbrParent,
  mergeFrbrEntities,
  splitFrbrEntity,
  searchFrbrEntities,
  type FrbrSearchResult,
} from "@/lib/api/admin";
import type { FrbrReassignPayload, FrbrMergePayload, FrbrSplitPayload } from "@/types/frbr";

type ActionTab = "reassign" | "merge" | "split";

interface RelationManagementDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entityType: "work" | "expression" | "manifestation" | "item";
  entityId: number;
  entityTitle: string;
  manifestationId?: number;
}

/**
 * Dialog for managing FRBR relations: reassign, merge, or split entities.
 *
 * @param props - Component properties
 * @returns The dialog JSX element
 */
export function RelationManagementDialog({
  open,
  onOpenChange,
  entityType,
  entityId,
  entityTitle,
  manifestationId,
}: RelationManagementDialogProps) {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<ActionTab>("reassign");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reassign state
  const [reassignParentType, setReassignParentType] = useState<"work" | "expression" | "manifestation">("work");
  const [reassignSearchQuery, setReassignSearchQuery] = useState("");
  const [reassignSearchResults, setReassignSearchResults] = useState<FrbrSearchResult[]>([]);
  const [reassignSelectedParent, setReassignSelectedParent] = useState<FrbrSearchResult | null>(null);
  const [isSearchingReassign, setIsSearchingReassign] = useState(false);

  // Merge state
  const [mergeSearchQuery, setMergeSearchQuery] = useState("");
  const [mergeSearchResults, setMergeSearchResults] = useState<FrbrSearchResult[]>([]);
  const [mergeSelectedTarget, setMergeSelectedTarget] = useState<FrbrSearchResult | null>(null);
  const [isSearchingMerge, setIsSearchingMerge] = useState(false);

  // Split state
  const [splitNewTitle, setSplitNewTitle] = useState("");
  const [splitChildIds, setSplitChildIds] = useState<string>("");

  // Determine which parent type is valid for reassign based on entity type
  useEffect(() => {
    if (entityType === "expression") {
      setReassignParentType("work");
    } else if (entityType === "manifestation") {
      setReassignParentType("expression");
    } else if (entityType === "item") {
      setReassignParentType("manifestation");
    }
  }, [entityType]);

  // Search for reassign target
  const handleReassignSearch = useCallback(async () => {
    if (!reassignSearchQuery.trim()) return;
    setIsSearchingReassign(true);
    try {
      const results = await searchFrbrEntities(reassignSearchQuery, reassignParentType, 10);
      setReassignSearchResults(results.filter(r => r.id !== entityId));
    } catch (err) {
      toast.error(`Search failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSearchingReassign(false);
    }
  }, [reassignSearchQuery, reassignParentType, entityId]);

  // Search for merge target
  const handleMergeSearch = useCallback(async () => {
    if (!mergeSearchQuery.trim()) return;
    setIsSearchingMerge(true);
    try {
      const results = await searchFrbrEntities(mergeSearchQuery, entityType as "work" | "expression" | "manifestation", 10);
      setMergeSearchResults(results.filter(r => r.id !== entityId));
    } catch (err) {
      toast.error(`Search failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSearchingMerge(false);
    }
  }, [mergeSearchQuery, entityType, entityId]);

  // Handle reassign submission
  const handleReassignSubmit = useCallback(async () => {
    if (!reassignSelectedParent) {
      toast.error("Please select a new parent entity");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: FrbrReassignPayload = {
        entity_type: entityType as "expression" | "manifestation" | "item",
        entity_id: entityId,
        new_parent_id: reassignSelectedParent.id,
      };
      await reassignFrbrParent(payload);
      toast.success(`Successfully reassigned ${entityType} to new parent`);
      if (manifestationId) {
        qc.invalidateQueries({ queryKey: ["frbr-tree", manifestationId] });
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(`Reassign failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [reassignSelectedParent, entityType, entityId, manifestationId, qc, onOpenChange]);

  // Handle merge submission
  const handleMergeSubmit = useCallback(async () => {
    if (!mergeSelectedTarget) {
      toast.error("Please select a target entity to merge into");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: FrbrMergePayload = {
        entity_type: entityType as "work" | "expression" | "manifestation",
        source_id: entityId,
        target_id: mergeSelectedTarget.id,
      };
      await mergeFrbrEntities(payload);
      toast.success(`Successfully merged ${entityType} into target`);
      if (manifestationId) {
        qc.invalidateQueries({ queryKey: ["frbr-tree", manifestationId] });
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(`Merge failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [mergeSelectedTarget, entityType, entityId, manifestationId, qc, onOpenChange]);

  // Handle split submission
  const handleSplitSubmit = useCallback(async () => {
    if (!splitNewTitle.trim()) {
      toast.error("Please provide a title for the new entity");
      return;
    }
    const childIds = splitChildIds
      .split(",")
      .map(s => parseInt(s.trim(), 10))
      .filter(n => !isNaN(n) && n > 0);
    if (childIds.length === 0) {
      toast.error("Please provide at least one valid child ID");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: FrbrSplitPayload = {
        entity_type: entityType as "work" | "expression" | "manifestation",
        source_id: entityId,
        child_ids: childIds,
        new_entity_attrs: { title: splitNewTitle.trim() },
      };
      await splitFrbrEntity(payload);
      toast.success(`Successfully split ${entityType} — new entity created`);
      if (manifestationId) {
        qc.invalidateQueries({ queryKey: ["frbr-tree", manifestationId] });
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(`Split failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [splitNewTitle, splitChildIds, entityType, entityId, manifestationId, qc, onOpenChange]);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setReassignSearchQuery("");
      setReassignSearchResults([]);
      setReassignSelectedParent(null);
      setMergeSearchQuery("");
      setMergeSearchResults([]);
      setMergeSelectedTarget(null);
      setSplitNewTitle("");
      setSplitChildIds("");
    }
  }, [open]);

  const tabs: { id: ActionTab; label: string; icon: React.ReactNode }[] = [
    { id: "reassign", label: "Reassign", icon: <ArrowRightLeft className="h-4 w-4" /> },
    { id: "merge", label: "Merge", icon: <Merge className="h-4 w-4" /> },
    { id: "split", label: "Split", icon: <SplitSquareVertical className="h-4 w-4" /> },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Manage FRBR Relations</DialogTitle>
          <DialogDescription>
            {entityType.charAt(0).toUpperCase() + entityType.slice(1)}: {entityTitle} (#{entityId})
          </DialogDescription>
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex gap-1 rounded-xl bg-secondary p-1">
          {tabs.map(({ id, label, icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition-all ${
                activeTab === id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* Reassign Tab */}
        {activeTab === "reassign" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Reassign Parent</CardTitle>
                <CardDescription>
                  Move this {entityType} to a different parent {reassignParentType}.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-2">
                  <input
                    placeholder={`Search for a ${reassignParentType}...`}
                    value={reassignSearchQuery}
                    onChange={e => setReassignSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleReassignSearch()}
                    className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleReassignSearch}
                    disabled={isSearchingReassign}
                  >
                    {isSearchingReassign ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  </Button>
                </div>
                {reassignSearchResults.length > 0 && (
                  <div className="max-h-40 overflow-y-auto rounded-md border">
                    {reassignSearchResults.map(r => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setReassignSelectedParent(r)}
                        className={`w-full px-3 py-2 text-left text-sm hover:bg-accent ${
                          reassignSelectedParent?.id === r.id ? "bg-accent" : ""
                        }`}
                      >
                        {r.title} (#{r.id})
                      </button>
                    ))}
                  </div>
                )}
                {reassignSelectedParent && (
                  <p className="text-sm text-muted-foreground">
                    Selected: <strong>{reassignSelectedParent.title}</strong> (#{reassignSelectedParent.id})
                  </p>
                )}
              </CardContent>
            </Card>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleReassignSubmit} disabled={isSubmitting || !reassignSelectedParent}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Reassign
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Merge Tab */}
        {activeTab === "merge" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Merge Into</CardTitle>
                <CardDescription>
                  Merge this {entityType} into another {entityType}. All children and contributions will be transferred.
                  This {entityType} will be deleted.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-2">
                  <input
                    placeholder={`Search for a ${entityType} to merge into...`}
                    value={mergeSearchQuery}
                    onChange={e => setMergeSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleMergeSearch()}
                    className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleMergeSearch}
                    disabled={isSearchingMerge}
                  >
                    {isSearchingMerge ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  </Button>
                </div>
                {mergeSearchResults.length > 0 && (
                  <div className="max-h-40 overflow-y-auto rounded-md border">
                    {mergeSearchResults.map(r => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setMergeSelectedTarget(r)}
                        className={`w-full px-3 py-2 text-left text-sm hover:bg-accent ${
                          mergeSelectedTarget?.id === r.id ? "bg-accent" : ""
                        }`}
                      >
                        {r.title} (#{r.id})
                      </button>
                    ))}
                  </div>
                )}
                {mergeSelectedTarget && (
                  <p className="text-sm text-muted-foreground">
                    Target: <strong>{mergeSelectedTarget.title}</strong> (#{mergeSelectedTarget.id})
                  </p>
                )}
              </CardContent>
            </Card>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleMergeSubmit} disabled={isSubmitting || !mergeSelectedTarget} variant="destructive">
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Merge & Delete
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Split Tab */}
        {activeTab === "split" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Split Children</CardTitle>
                <CardDescription>
                  Create a new {entityType} and move selected children into it. The new entity inherits the same parent.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-sm font-medium">New entity title</label>
                  <input
                    placeholder="Enter title for the new entity..."
                    value={splitNewTitle}
                    onChange={e => setSplitNewTitle(e.target.value)}
                    className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Child IDs to move (comma-separated)</label>
                  <input
                    placeholder="e.g. 12, 34, 56"
                    value={splitChildIds}
                    onChange={e => setSplitChildIds(e.target.value)}
                    className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
              </CardContent>
            </Card>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleSplitSubmit} disabled={isSubmitting || !splitNewTitle.trim() || !splitChildIds.trim()}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Split
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
