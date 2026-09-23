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

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import {
  Loader2,
  RotateCcw,
  X,
} from "lucide-react";
import Link from "next/link";
import { useProfile, useFrbrTree, useUpdateFrbrEntity, useDeleteFrbrEntity } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { PermissionName } from "@/lib/permissions";
import { useCreateEscalation } from "@/lib/api/escalations";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { WorkEditor } from "./frbr/work-editor";
import { ExpressionEditor } from "./frbr/expression-editor";
import { ManifestationEditor } from "./frbr/manifestation-editor";
import { ItemsManager } from "./frbr/items-manager";
import { FRBRTreeView, type FrbrLevel } from "./frbr/frbr-tree-view";
import {
  transformFieldsToMeta,
  type WorkFormData,
  type ExpressionFormData,
  type ManifestationFormData,
  type ItemFormData,
} from "./frbr/types";

// ---------------------------------------------------------------------------
// Name normalization — must match backend ``normalize_contributor_name`` rules
// ---------------------------------------------------------------------------

/** Cultural surname particles that remain lowercase when interior. */
const NAME_PARTICLES = new Set([
  "van", "von", "der", "den", "de", "del", "da", "di", "du",
  "la", "le", "lo", "te", "ter", "ten",
]);

/**
 * Capitalize a single name token according to FRBR cataloging rules.
 *
 * Handles hyphenated compounds, single-letter initials, and cultural
 * particles that remain lowercase when they appear as interior words.
 *
 * @param word - The name token to capitalize
 * @param isFirst - Whether this is the first word in the name
 * @returns The capitalized word
 */
function capitalizeNameWord(word: string, isFirst: boolean): string {
  if (!word) return word;

  // Hyphenated compound: capitalize each segment independently.
  if (word.includes("-")) {
    return word
      .split("-")
      .map((seg, idx) => capitalizeNameWord(seg, isFirst && idx === 0))
      .join("-");
  }

  const lower = word.toLowerCase();

  // Interior cultural particle stays lowercase.
  if (!isFirst && NAME_PARTICLES.has(lower)) {
    return lower;
  }

  // Single-letter initial (``j`` or ``j.``) → ``J.``
  if (/^[a-zA-Z]\.?$/.test(word)) {
    return lower.toUpperCase() + (word.endsWith(".") ? "" : ".");
  }

  // Default: capitalize first letter, lowercase the rest.
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/**
 * Normalize whitespace and capitalize a contributor display name.
 *
 * Mirrors the backend :func:`normalize_contributor_name` logic so that
 * client-side previews and server-side persistence agree.
 *
 * @param name - Raw contributor name input
 * @returns Normalized display name
 */
export function normalizeContributorName(name: string): string {
  if (!name) return "";
  const cleaned = name.trim().replace(/\s+/g, " ");
  if (!cleaned) return "";

  const words = cleaned.split(" ");
  const capitalized: string[] = [];

  // Detect initials-only prefix so we can collapse "j. r. r." → "J.R.R."
  let initialRunEnd = 0;
  for (let idx = 0; idx < words.length; idx++) {
    const bare = words[idx].replace(/\.$/, "");
    if (bare.length === 1 && /[a-zA-Z]/.test(bare)) {
      initialRunEnd = idx + 1;
    } else {
      break;
    }
  }

  if (initialRunEnd > 1) {
    const collapsed = words
      .slice(0, initialRunEnd)
      .map(w => w.replace(/\.$/, "").toUpperCase() + ".")
      .join("");
    capitalized.push(collapsed);
  }

  for (let idx = initialRunEnd; idx < words.length; idx++) {
    const isFirst = capitalized.length === 0;
    capitalized.push(capitalizeNameWord(words[idx], isFirst));
  }

  return capitalized.join(" ");
}

interface FrbrEditorProps {
  manifestationId: number;
  onClose?: () => void;
}

/**
 * Main FRBR Editor component that orchestrates the decomposed sub-components.
 * Uses TanStack Query for data fetching and optimistic cache updates.
 *
 * @param props - Component properties
 * @param props.manifestationId - The manifestation ID to load
 * @param props.onClose - Optional callback when the editor is closed
 * @returns FRBR editor JSX element
 */
export function FrbrEditor({ manifestationId, onClose }: FrbrEditorProps) {
  const { data: tree, isLoading, isError, error, refetch } = useFrbrTree(manifestationId);
  const updateEntity = useUpdateFrbrEntity();
  const deleteEntity = useDeleteFrbrEntity();
  const { data: profile } = useProfile();
  const createEscalation = useCreateEscalation();
  const hasWriteMetadata = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const hasEscalateRequest = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));

  const [activeTab, setActiveTab] = useState<"work" | "expression" | "manifestation" | "items">("manifestation");
  const [lastFetched, setLastFetched] = useState(0);

  // Add Child dialog state
  const [addChildDialog, setAddChildDialog] = useState<{
    open: boolean;
    parentLevel: FrbrLevel | null;
  }>({ open: false, parentLevel: null });
  const [newChildTitle, setNewChildTitle] = useState("");

  // Delete confirmation dialog state
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    level: FrbrLevel | null;
    id: number | null;
  }>({ open: false, level: null, id: null });

  // Escalate dialog state
  const [escalateDialog, setEscalateDialog] = useState<{
    open: boolean;
    level: FrbrLevel | null;
    id: number | null;
  }>({ open: false, level: null, id: null });
  const [escalationNote, setEscalationNote] = useState("");

  const handleWorkSubmit = useCallback(
    async (data: WorkFormData) => {
      if (!tree?.work) return;
      try {
        const meta = transformFieldsToMeta(data.metaFields);
        await updateEntity.mutateAsync({
          manifestationId,
          type: "work",
          id: tree.work.id,
          data: { title: data.title, meta, contributions: data.contributions },
        });
        setLastFetched(Date.now());
        toast.success("Work updated successfully");
      } catch (err) {
        toast.error(`Failed to update work: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    },
    [tree, manifestationId, updateEntity]
  );

  const handleExpressionSubmit = useCallback(
    async (data: ExpressionFormData) => {
      if (!tree?.expression) return;
      try {
        const meta = transformFieldsToMeta(data.metaFields);
        await updateEntity.mutateAsync({
          manifestationId,
          type: "expression",
          id: tree.expression.id,
          data: {
            content_type: data.content_type,
            language: data.language,
            kind: data.kind,
            meta,
            contributions: data.contributions,
          },
        });
        setLastFetched(Date.now());
        toast.success("Expression updated successfully");
      } catch (err) {
        toast.error(`Failed to update expression: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    },
    [tree, manifestationId, updateEntity]
  );

  const handleManifestationSubmit = useCallback(
    async (data: ManifestationFormData) => {
      if (!tree?.manifestation) return;
      try {
        const originalType = tree.manifestation.meta?.type as string;
        const typeChanged = data.type && data.type !== originalType;

        if (!hasWriteMetadata) {
          if (typeChanged && hasEscalateRequest) {
            await createEscalation.mutateAsync({
              level: "manifestation",
              targetId: tree.manifestation.id,
              data: {
                request_type: "change_type",
                field_name: "type",
                current_value: originalType,
                suggested_value: data.type ?? "",
                note: "Type change suggested via editor",
              },
            });
            toast.success("Type change requested via User Requests.");
          } else {
            toast.error("You do not have permission to update metadata.");
          }
          return;
        }

        const meta = transformFieldsToMeta(data.metaFields);
        if (data.type) {
          meta.type = data.type;
        }

        await updateEntity.mutateAsync({
          manifestationId,
          type: "manifestation",
          id: tree.manifestation.id,
          data: {
            isbn13: data.isbn13,
            upc: data.upc,
            ean: data.ean,
            publisher: data.publisher,
            publication_date: data.publication_date,
            meta,
            contributions: data.contributions,
          },
        });
        setLastFetched(Date.now());
        toast.success("Manifestation updated successfully");
      } catch (err) {
        toast.error(`Failed to update manifestation: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    },
    [tree, manifestationId, updateEntity, hasWriteMetadata, hasEscalateRequest, createEscalation]
  );

  const handleItemSubmit = useCallback(
    async (data: ItemFormData, itemId: number) => {
      try {
        const meta = transformFieldsToMeta(data.metaFields);
        await updateEntity.mutateAsync({
          manifestationId,
          type: "item",
          id: itemId,
          data: {
            status: data.status,
            condition: data.condition,
            meta,
          },
        });
        setLastFetched(Date.now());
        toast.success("Item updated successfully");
      } catch (err) {
        toast.error(`Failed to update item: ${err instanceof Error ? err.message : "Unknown error"}`);
      }
    },
    [manifestationId, updateEntity]
  );

  /**
   * Handles the "Add Child" action from the tree view or editor toolbars.
   *
   * @param parentLevel - The parent entity level
   */
  const handleAddChild = useCallback((parentLevel: FrbrLevel) => {
    setAddChildDialog({ open: true, parentLevel });
    setNewChildTitle("");
  }, []);

  /**
   * Confirms the creation of a new child entity.
   */
  const confirmAddChild = useCallback(async () => {
    if (!addChildDialog.parentLevel || !tree || !newChildTitle.trim()) return;
    const parentLevel = addChildDialog.parentLevel;

    try {
      let parentId: number;
      let childType: string;

      if (parentLevel === "work" && tree.work) {
        parentId = tree.work.id;
        childType = "expression";
      } else if (parentLevel === "expression" && tree.expression) {
        parentId = tree.expression.id;
        childType = "manifestation";
      } else if (parentLevel === "manifestation") {
        parentId = tree.manifestation.id;
        childType = "item";
      } else {
        return;
      }

      await apiClient.post(`/v1/admin/frbr/${parentLevel}/${parentId}/${childType}`, {
        title: newChildTitle.trim(),
      });
      toast.success(`Created new ${childType}`);
      setAddChildDialog({ open: false, parentLevel: null });
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create child entity");
    }
  }, [addChildDialog.parentLevel, tree, newChildTitle, refetch]);

  /**
   * Handles the "Escalate" action.
   *
   * @param level - The entity level
   * @param id - The entity ID
   */
  const handleEscalate = useCallback((level: FrbrLevel, id: number) => {
    setEscalateDialog({ open: true, level, id });
    setEscalationNote("");
  }, []);

  /**
   * Confirms the escalation request.
   */
  const confirmEscalation = useCallback(async () => {
    if (!escalateDialog.level || !escalateDialog.id) return;
    try {
      await createEscalation.mutateAsync({
        level: escalateDialog.level,
        targetId: escalateDialog.id,
        data: {
          field_name: "general",
          suggested_value: "",
          note: escalationNote || "Escalation requested via editor",
        },
      });
      toast.success("Escalation request submitted");
      setEscalateDialog({ open: false, level: null, id: null });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit escalation");
    }
  }, [escalateDialog, createEscalation, escalationNote]);

  /**
   * Handles the "Delete" action.
   *
   * @param level - The entity level
   * @param id - The entity ID
   */
  const handleDelete = useCallback((level: FrbrLevel, id: number) => {
    setDeleteDialog({ open: true, level, id });
  }, []);

  /**
   * Confirms the entity deletion.
   */
  const confirmDelete = useCallback(async () => {
    if (!deleteDialog.level || !deleteDialog.id) return;
    try {
      await deleteEntity.mutateAsync({
        manifestationId,
        type: deleteDialog.level,
        id: deleteDialog.id,
      });
      toast.success("Entity deleted");
      setDeleteDialog({ open: false, level: null, id: null });
      setActiveTab("manifestation");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete entity");
    }
  }, [deleteDialog, manifestationId, deleteEntity]);

  /**
   * Handles tree node selection.
   *
   * @param level - The selected entity level
   */
  const handleTreeSelect = useCallback((level: FrbrLevel) => {
    if (level === "item") {
      setActiveTab("items");
    } else {
      setActiveTab(level);
    }
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin w-8 h-8" />
      </div>
    );
  }

  if (isError || !tree) {
    return (
      <div className="text-center p-8">
        <p className="text-destructive">{error?.message ?? "Failed to load FRBR hierarchy"}</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          <RotateCcw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center bg-muted/50 p-2 rounded-lg">
        <Select
          value={activeTab}
          onValueChange={(value: "work" | "expression" | "manifestation" | "items") => setActiveTab(value)}
        >
          <SelectTrigger className="w-[200px] bg-background">
            <SelectValue placeholder="Select level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="work">Work (F1)</SelectItem>
            <SelectItem value="expression">Expression (F2)</SelectItem>
            <SelectItem value="manifestation">Manifestation (F3)</SelectItem>
            <SelectItem value="items">Items (F5)</SelectItem>
          </SelectContent>
        </Select>
        {onClose && (
          <Button type="button" variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        )}
      </div>
      <FRBRTreeView
        tree={tree}
        selectedLevel={activeTab === "items" ? "item" : activeTab}
        onSelect={(level) => handleTreeSelect(level)}
        onAddChild={handleAddChild}
        onEscalate={handleEscalate}
        onDelete={handleDelete}
      />

      {activeTab === "work" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Work</CardTitle>
            <CardDescription>The creative foundation (F1 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.work ? (
              <WorkEditor
                key={`${tree.work.id}-${lastFetched}`}
                tree={tree}
                onSubmit={handleWorkSubmit}
                onAddChild={() => handleAddChild("work")}
                onEscalate={hasEscalateRequest ? () => handleEscalate("work", tree.work!.id) : undefined}
                onDelete={hasWriteMetadata ? () => handleDelete("work", tree.work!.id) : undefined}
              />
            ) : (
              <p className="text-muted-foreground">No Work associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "expression" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Expression</CardTitle>
            <CardDescription>The intellectual artistic form (F2 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.expression ? (
              <ExpressionEditor
                key={`${tree.expression.id}-${lastFetched}`}
                tree={tree}
                onSubmit={handleExpressionSubmit}
                onAddChild={() => handleAddChild("expression")}
                onEscalate={hasEscalateRequest ? () => handleEscalate("expression", tree.expression!.id) : undefined}
                onDelete={hasWriteMetadata ? () => handleDelete("expression", tree.expression!.id) : undefined}
              />
            ) : (
              <p className="text-muted-foreground">No Expression associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "manifestation" && (
        <Card>
          <CardHeader>
            <CardTitle>
              Edit Manifestation{" "}
              <Link
                href={`/manifestation/${tree.manifestation.id}`}
                className="text-muted-foreground hover:underline hover:text-primary transition-colors"
                target="_blank"
              >
                #{tree.manifestation.id}
              </Link>
            </CardTitle>
            <CardDescription>The physical embodiment (F3 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            <ManifestationEditor
              key={`${tree.manifestation.id}-${lastFetched}`}
              tree={tree}
              onSubmit={handleManifestationSubmit}
              onAddChild={() => handleAddChild("manifestation")}
              onEscalate={hasEscalateRequest ? () => handleEscalate("manifestation", tree.manifestation.id) : undefined}
              onDelete={hasWriteMetadata ? () => handleDelete("manifestation", tree.manifestation.id) : undefined}
            />
          </CardContent>
        </Card>
      )}

      {activeTab === "items" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Items</CardTitle>
            <CardDescription>Individual copies (F5 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            <ItemsManager
              items={tree.items}
              onItemSubmit={handleItemSubmit}
              onItemEscalate={hasEscalateRequest ? (itemId) => handleEscalate("item", itemId) : undefined}
              onItemDelete={hasWriteMetadata ? (itemId) => handleDelete("item", itemId) : undefined}
              lastFetched={lastFetched}
            />
          </CardContent>
        </Card>
      )}

      {/* Add Child Dialog */}
      <Dialog open={addChildDialog.open} onOpenChange={open => setAddChildDialog(prev => ({ ...prev, open }))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Add Child {addChildDialog.parentLevel === "work" ? "Expression" : addChildDialog.parentLevel === "expression" ? "Manifestation" : "Item"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <input
              placeholder="Enter title..."
              value={newChildTitle}
              onChange={e => setNewChildTitle(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <Button onClick={confirmAddChild} disabled={!newChildTitle.trim()}>
              Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialog.open} onOpenChange={open => setDeleteDialog(prev => ({ ...prev, open }))}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {deleteDialog.level}?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the {deleteDialog.level} entity
              {deleteDialog.level === "work" ? " and all its expressions, manifestations, and items" : ""}
              {deleteDialog.level === "expression" ? " and all its manifestations and items" : ""}
              {deleteDialog.level === "manifestation" ? " and all its items" : ""}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Escalate Dialog */}
      <Dialog open={escalateDialog.open} onOpenChange={open => setEscalateDialog(prev => ({ ...prev, open }))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Escalation</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <textarea
              placeholder="Describe the change you are requesting..."
              value={escalationNote}
              onChange={e => setEscalationNote(e.target.value)}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <Button onClick={confirmEscalation}>Submit Request</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
