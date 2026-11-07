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
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

import { useCreateNewMediaTypeEscalation, createNewMediaTypeEscalation } from "@/lib/api/escalations";
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

interface RequestNewTypeModalProps {
  defaultSampleIdentifier?: string;
  trigger?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * Modal form for collectors to request a new media category or physical format.
 *
 * @param props - Component props.
 * @param props.defaultSampleIdentifier - Optional default barcode or identifier (e.g. from /scan).
 * @param props.trigger - Custom trigger element if uncontrolled or embedded.
 * @param props.open - Controlled open state.
 * @param props.onOpenChange - Open state callback.
 * @param props.onSuccess - Callback invoked after successful proposal submission.
 * @returns Dialog element for proposing a new media type.
 */
export function RequestNewTypeModal({
  defaultSampleIdentifier = "",
  trigger,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  onSuccess,
}: RequestNewTypeModalProps) {
  const t = useTranslations("HelpRequests");
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;
  const setOpen = isControlled ? (controlledOnOpenChange ?? (() => {})) : setInternalOpen;

  const [proposedCategory, setProposedCategory] = useState("");
  const [proposedFormat, setProposedFormat] = useState("");
  const [parentFrbrClass, setParentFrbrClass] = useState<"F1_Work" | "F16_Container_Work">("F1_Work");
  const [sampleIdentifier, setSampleIdentifier] = useState(defaultSampleIdentifier);
  const [rationale, setRationale] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  let createMutation: ReturnType<typeof useCreateNewMediaTypeEscalation> | null = null;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    createMutation = useCreateNewMediaTypeEscalation();
  } catch {
    createMutation = null;
  }

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setTimeout(() => {
        setSubmitted(false);
        setErrorMsg("");
        setIsSubmitting(false);
        setProposedCategory("");
        setProposedFormat("");
        setParentFrbrClass("F1_Work");
        setSampleIdentifier(defaultSampleIdentifier);
        setRationale("");
      }, 200);
    } else {
      if (defaultSampleIdentifier && !sampleIdentifier) {
        setSampleIdentifier(defaultSampleIdentifier);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!proposedCategory.trim() || !proposedFormat.trim() || !rationale.trim()) {
      setErrorMsg(t("allRequiredFieldsError") || "Please fill in all required fields.");
      return;
    }

    setErrorMsg("");
    const payload = {
      proposed_category: proposedCategory.trim(),
      proposed_format: proposedFormat.trim(),
      parent_frbr_class: parentFrbrClass,
      sample_identifier_or_url: sampleIdentifier.trim() || undefined,
      rationale: rationale.trim(),
    };

    if (createMutation) {
      createMutation.mutate(payload, {
        onSuccess: () => {
          setSubmitted(true);
          toast.success(t("newMediaTypeSubmittedToast") || "New media type request submitted to custodians");
          onSuccess?.();
        },
        onError: err => {
          const msg = err instanceof Error ? err.message : t("failedToSubmit");
          setErrorMsg(msg);
          toast.error(msg);
        },
      });
      return;
    }

    // Direct fallback if mounted without QueryClientProvider (e.g. lightweight isolated unit tests)
    setIsSubmitting(true);
    try {
      await createNewMediaTypeEscalation(payload);
      setSubmitted(true);
      toast.success(t("newMediaTypeSubmittedToast") || "New media type request submitted to custodians");
      onSuccess?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("failedToSubmit");
      setErrorMsg(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPending = Boolean(createMutation?.isPending || isSubmitting);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {trigger ? (
        <DialogTrigger asChild>{trigger}</DialogTrigger>
      ) : !isControlled ? (
        <DialogTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="inline-flex items-center gap-1.5 text-xs text-primary border-primary/30 hover:bg-primary/5"
            data-testid="request-new-type-trigger"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>{t("requestNewMediaType") || "Request New Media Type"}</span>
          </Button>
        </DialogTrigger>
      ) : null}

      <DialogContent className="sm:max-w-lg" data-testid="request-new-type-modal">
        {submitted ? (
          <div className="flex flex-col items-center justify-center py-6 text-center space-y-3">
            <CheckCircle2 className="h-10 w-10 text-emerald-500 animate-in zoom-in" />
            <h4 className="text-base font-semibold text-foreground">
              {t("requestSubmittedTitle") || "Proposal Submitted"}
            </h4>
            <p className="text-xs text-muted-foreground max-w-sm">
              {t("newMediaTypeSubmittedDesc") ||
                "Thank you! Instance custodians have been notified. You can track this request in your Requests tab."}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleOpenChange(false)}
              className="mt-2 text-xs"
            >
              {t("confirm") || "Close"}
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-primary" />
                <span>{t("requestNewMediaTypeTitle") || "Request New Media Type or Format"}</span>
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                {t("requestNewMediaTypeDesc") ||
                  "Propose a new media category or physical format not yet supported in iqoqo. Custodians will review and adapt the ontology."}
              </DialogDescription>
            </DialogHeader>

            {errorMsg && (
              <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-2.5 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="space-y-1">
                <label htmlFor="proposed-category" className="font-semibold text-foreground">
                  {t("proposedCategoryLabel") || "Proposed Category"} *
                </label>
                <input
                  id="proposed-category"
                  data-testid="proposed-category-input"
                  required
                  type="text"
                  value={proposedCategory}
                  onChange={e => setProposedCategory(e.target.value)}
                  placeholder="e.g. Lego Sets, Sheet Music, Film Roll"
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="proposed-format" className="font-semibold text-foreground">
                  {t("proposedFormatLabel") || "Proposed Format"} *
                </label>
                <input
                  id="proposed-format"
                  data-testid="proposed-format-input"
                  required
                  type="text"
                  value={proposedFormat}
                  onChange={e => setProposedFormat(e.target.value)}
                  placeholder="e.g. Standard Box, 35mm Slide, 7-inch Vinyl"
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </div>

            <div className="space-y-1 text-xs">
              <label htmlFor="parent-frbr-class" className="font-semibold text-foreground">
                {t("parentFrbrClassLabel") || "Ontology FRBR Class"}
              </label>
              <select
                id="parent-frbr-class"
                data-testid="parent-frbr-class-select"
                value={parentFrbrClass}
                onChange={e => setParentFrbrClass(e.target.value as "F1_Work" | "F16_Container_Work")}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="F1_Work">F1 Work (Individual creative / physical object)</option>
                <option value="F16_Container_Work">F16 Container Work (Boxed set / multi-item container)</option>
              </select>
            </div>

            <div className="space-y-1 text-xs">
              <label htmlFor="sample-identifier" className="font-semibold text-foreground">
                {t("sampleIdentifierLabel") || "Sample Barcode, Identifier or URL"}
              </label>
              <input
                id="sample-identifier"
                data-testid="sample-identifier-input"
                type="text"
                value={sampleIdentifier}
                onChange={e => setSampleIdentifier(e.target.value)}
                placeholder="e.g. 5702016913507, https://bricklink.com/..., ISBN"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            <div className="space-y-1 text-xs">
              <label htmlFor="rationale-note" className="font-semibold text-foreground">
                {t("rationaleLabel") || "Rationale & Why it should be added"} *
              </label>
              <textarea
                id="rationale-note"
                data-testid="rationale-input"
                required
                rows={3}
                value={rationale}
                onChange={e => setRationale(e.target.value)}
                placeholder="Describe how collectors catalog this media type, what attributes it has, or why existing formats don't fit."
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            <DialogFooter className="flex-row justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleOpenChange(false)}
                disabled={isPending}
                className="text-xs"
              >
                {t("cancel") || "Cancel"}
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isPending || !proposedCategory.trim() || !proposedFormat.trim()}
                className="text-xs gap-1"
                data-testid="submit-new-type-btn"
              >
                {isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>{t("submitting") || "Submitting..."}</span>
                  </>
                ) : (
                  <span>{t("submitRequest") || "Submit Request"}</span>
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
