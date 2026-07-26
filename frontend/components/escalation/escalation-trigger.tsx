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
import { HelpCircle, CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import { useCreateEscalation, useMyEscalations } from "@/lib/api/escalations";
import type { EscalationRequest } from "@/types/frbr";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface EscalationTriggerProps {
  level: "work" | "expression" | "manifestation" | "item";
  targetId: number;
  /** Pre-filtered escalations for this target. When provided, internal fetch is skipped. */
  escalations?: EscalationRequest[];
  /** When true, show only the dialog button (no status card). Useful inside accordions. */
  alwaysShowDialog?: boolean;
}

/**
 * Component rendering the "Ask custodians for help" trigger button or active escalation status card.
 *
 * @param props - Component props.
 * @param props.level - The FRBR entity level.
 * @param props.targetId - The target entity ID.
 * @param props.escalations - Optional pre-filtered escalations for this target. When provided, internal fetch is skipped.
 * @param props.alwaysShowDialog - When true, show only the dialog button (no status card). Useful inside accordions.
 * @returns The rendered trigger button, status card, or null.
 */
export function EscalationTrigger({
  level,
  targetId,
  escalations: providedEscalations,
  alwaysShowDialog = false,
}: EscalationTriggerProps) {
  const { data: profile } = useProfile();
  const t = useTranslations("HelpRequests");
  const [open, setOpen] = useState(false);
  const [requestType, setRequestType] = useState<"correction" | "deletion" | "CHANGE_TYPE">("correction");
  const [fieldName, setFieldName] = useState("title");
  const [currentValue, setCurrentValue] = useState("");
  const [suggestedValue, setSuggestedValue] = useState("");
  const [note, setNote] = useState("");

  const hasWriteMetadata = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const hasEscalateRequest = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));

  const shouldFetch = hasEscalateRequest && !providedEscalations;
  const { data: myEscalations } = useMyEscalations(shouldFetch);
  const createMutation = useCreateEscalation();

  const handleTypeChange = (newType: "correction" | "deletion" | "CHANGE_TYPE") => {
    setRequestType(newType);
    if (newType === "CHANGE_TYPE") {
        setFieldName("type");
    } else {
        setFieldName("title");
    }
    setCurrentValue("");
    setSuggestedValue("");
    setNote("");
  };

  // If user has direct write access or lacks escalate permission, do not render trigger
  if (hasWriteMetadata || !hasEscalateRequest) {
    return null;
  }

  // Use provided escalations if available, otherwise find from fetched
  const allTargetEscalations =
    providedEscalations ??
    myEscalations?.filter(e => {
      if (level === "work") return e.work_id === targetId;
      if (level === "expression") return e.expression_id === targetId;
      if (level === "manifestation") return e.manifestation_id === targetId;
      if (level === "item") return e.item_id === targetId;
      return false;
    }) ??
    [];

  // When alwaysShowDialog is true, skip status card rendering entirely.
  // In standalone mode, show status card for first matching escalation (any status).
  const activeEscalation = alwaysShowDialog
    ? undefined
    : allTargetEscalations.length > 0
      ? allTargetEscalations[0]
      : undefined;

  if (activeEscalation) {
    const isDeletion = activeEscalation.request_type === "deletion" || !activeEscalation.field_name;
    const getStatusIcon = () => {
      switch (activeEscalation.status) {
        case "accepted":
          return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
        case "rejected":
          return <XCircle className="h-4 w-4 text-destructive" />;
        case "duplicate":
          return <AlertCircle className="h-4 w-4 text-amber-500" />;
        default:
          return <Clock className="h-4 w-4 text-amber-500 animate-pulse" />;
      }
    };

    return (
      <div
        data-testid="escalation-status-card"
        className="rounded-lg border border-border bg-card p-3 text-xs shadow-xs space-y-1.5"
      >
        <div className="flex items-center justify-between font-medium">
          <span className="flex items-center gap-1.5 capitalize">
            {getStatusIcon()}
            {t("helpRequest")}: {t(activeEscalation.status)}
          </span>
          <span className="text-muted-foreground uppercase text-[10px] tracking-wider font-mono">
            {isDeletion ? t("deletion") : activeEscalation.field_name}
          </span>
        </div>
        {isDeletion ? (
          <div className="text-muted-foreground">
            {t("reasonForDeletion")}: <span className="text-foreground">{activeEscalation.note || "—"}</span>
          </div>
        ) : (
          <div className="text-muted-foreground">
            {t("suggested")}: <span className="font-mono text-foreground">{activeEscalation.suggested_value}</span>
          </div>
        )}
        {activeEscalation.resolution_note && (
          <div className="rounded bg-muted/50 p-1.5 text-[11px] italic text-muted-foreground border-l-2 border-primary/50">
            Custodian note: &ldquo;{activeEscalation.resolution_note}&rdquo;
          </div>
        )}
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (requestType === "deletion") {
      if (!note.trim()) {
        toast.error(t("reasonForDeletionRequired") || "Reason for deletion is required");
        return;
      }
    } else {
      if (!suggestedValue.trim()) {
        toast.error(t("suggestedValueRequired"));
        return;
      }
    }

    createMutation.mutate(
      {
        level,
        targetId,
        data: {
          request_type: requestType,
          field_name: requestType === "deletion" ? "" : fieldName,
          current_value: requestType === "deletion" ? undefined : currentValue.trim() || undefined,
          suggested_value: requestType === "deletion" ? "" : suggestedValue.trim(),
          note: note.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(requestType === "deletion" ? t("deletionRequestSubmitted") : t("escalationSubmitted"));
          setOpen(false);
          setRequestType("correction");
          setSuggestedValue("");
          setCurrentValue("");
          setNote("");
        },
        onError: err => {
          toast.error(err instanceof Error ? err.message : t("failedToSubmit"));
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full justify-start gap-2">
          <HelpCircle className="h-4 w-4 text-muted-foreground" />
          <span>{t("askCustodiansForHelp")}</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {requestType === "deletion" ? t("requestDeletion") : requestType === "CHANGE_TYPE" ? "Change Type" : t("requestMetadataCorrection")}
            </DialogTitle>
            <DialogDescription>{t("requestDescription")}</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="flex rounded-md bg-muted p-1 gap-1">
              <button
                type="button"
                className={`flex-1 rounded-xs px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  requestType === "correction"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => handleTypeChange("correction")}
              >
                {t("metadataCorrection")}
              </button>
              <button
                type="button"
                className={`flex-1 rounded-xs px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  requestType === "deletion"
                    ? "bg-background text-destructive shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => handleTypeChange("deletion")}
              >
                {t("requestDeletion")}
              </button>
              <button
                type="button"
                className={`flex-1 rounded-xs px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  requestType === "CHANGE_TYPE"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => handleTypeChange("CHANGE_TYPE")}
              >
                Change Type
              </button>
            </div>

            {requestType === "deletion" ? (
              <div className="grid gap-2">
                <label htmlFor="deletion_note" className="text-xs font-medium">
                  {t("reasonForDeletion")} <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="deletion_note"
                  placeholder={t("reasonForDeletionPlaceholder")}
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  rows={4}
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  required
                />
              </div>
            ) : (
              <>
                <div className="grid gap-2">
                  <label htmlFor="field_name" className="text-xs font-medium">
                    {requestType === "CHANGE_TYPE" ? "Field" : t("fieldToCorrect")}
                  </label>
                  <select
                    id="field_name"
                    value={fieldName}
                    disabled={requestType === "CHANGE_TYPE"}
                    onChange={e => setFieldName(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="title">Title</option>
                    <option value="type">Entity Type</option>
                    <option value="isbn">ISBN / Identifier</option>
                    <option value="format">Format / Classification</option>
                    <option value="author">Author / Creator</option>
                    <option value="year">Publication Year</option>
                    <option value="other">Other metadata</option>
                  </select>
                </div>
                <div className="grid gap-2">
                  <label htmlFor="current_value" className="text-xs font-medium">
                    {t("currentValueOptional")}
                  </label>
                  <input
                    id="current_value"
                    type="text"
                    placeholder="Current incorrect value"
                    value={currentValue}
                    onChange={e => setCurrentValue(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="suggested_value" className="text-xs font-medium">
                    {t("suggestedValue")} <span className="text-destructive">*</span>
                  </label>
                  <input
                    id="suggested_value"
                    type="text"
                    placeholder="Correct value"
                    value={suggestedValue}
                    onChange={e => setSuggestedValue(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <label htmlFor="note" className="text-xs font-medium">
                    {t("reasonNoteOptional")}
                  </label>
                  <textarea
                    id="note"
                    placeholder="Why should this field be changed? Provide sources or context."
                    value={note}
                    onChange={e => setNote(e.target.value)}
                    rows={3}
                    className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? t("submitting") : t("submitRequest")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
