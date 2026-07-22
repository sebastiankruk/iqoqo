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

import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import { useCreateEscalation, useMyEscalations } from "@/lib/api/escalations";
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
}

/**
 * Component rendering the "Ask custodians for help" trigger button or active escalation status card.
 *
 * @param props - Component props.
 * @param props.level - The FRBR entity level.
 * @param props.targetId - The target entity ID.
 * @returns The rendered trigger button, status card, or null.
 */
export function EscalationTrigger({ level, targetId }: EscalationTriggerProps) {
  const { data: profile } = useProfile();
  const [open, setOpen] = useState(false);
  const [fieldName, setFieldName] = useState("title");
  const [currentValue, setCurrentValue] = useState("");
  const [suggestedValue, setSuggestedValue] = useState("");
  const [note, setNote] = useState("");

  const hasWriteMetadata = Boolean(profile?.permissions?.includes(PermissionName.WRITE_METADATA));
  const hasEscalateRequest = Boolean(profile?.permissions?.includes(PermissionName.ESCALATE_REQUEST));

  const { data: myEscalations } = useMyEscalations(hasEscalateRequest);
  const createMutation = useCreateEscalation();

  // If user has direct write access or lacks escalate permission, do not render trigger
  if (hasWriteMetadata || !hasEscalateRequest) {
    return null;
  }

  // Find active or recent escalation for this target
  const activeEscalation = myEscalations?.find(e => {
    if (level === "work") return e.work_id === targetId;
    if (level === "expression") return e.expression_id === targetId;
    if (level === "manifestation") return e.manifestation_id === targetId;
    if (level === "item") return e.item_id === targetId;
    return false;
  });

  if (activeEscalation) {
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
            Escalation: {activeEscalation.status}
          </span>
          <span className="text-muted-foreground uppercase text-[10px] tracking-wider font-mono">
            {activeEscalation.field_name}
          </span>
        </div>
        <div className="text-muted-foreground">
          Suggested: <span className="font-mono text-foreground">{activeEscalation.suggested_value}</span>
        </div>
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
    if (!suggestedValue.trim()) {
      toast.error("Suggested value is required");
      return;
    }

    createMutation.mutate(
      {
        level,
        targetId,
        data: {
          field_name: fieldName,
          current_value: currentValue.trim() || undefined,
          suggested_value: suggestedValue.trim(),
          note: note.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Escalation request submitted to custodians");
          setOpen(false);
          setSuggestedValue("");
          setCurrentValue("");
          setNote("");
        },
        onError: err => {
          toast.error(err instanceof Error ? err.message : "Failed to submit escalation request");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full justify-start gap-2">
          <HelpCircle className="h-4 w-4 text-muted-foreground" />
          <span>Ask custodians for help</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Request Metadata Correction</DialogTitle>
            <DialogDescription>
              Submit a request to custodians to review and update locked metadata on this entity.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="field_name" className="text-xs font-medium">
                Field to correct
              </label>
              <select
                id="field_name"
                value={fieldName}
                onChange={e => setFieldName(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="title">Title</option>
                <option value="isbn">ISBN / Identifier</option>
                <option value="format">Format / Classification</option>
                <option value="author">Author / Creator</option>
                <option value="year">Publication Year</option>
                <option value="other">Other metadata</option>
              </select>
            </div>
            <div className="grid gap-2">
              <label htmlFor="current_value" className="text-xs font-medium">
                Current value (optional)
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
                Suggested value <span className="text-destructive">*</span>
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
                Reason / Note (optional)
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
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Submitting..." : "Submit Request"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
