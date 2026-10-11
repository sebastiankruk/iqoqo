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
import { toast } from "sonner";
import { Loader2, GitMerge } from "lucide-react";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { mergeCustodianProviderMetadata, type FrbrTree, type CustodianProviderMergeSelections } from "@/lib/api/admin";
import { queryKeys } from "@/lib/api/hooks/query-keys";

export interface ProviderCandidate {
  provider: string;
  providerLabel: string;
  value: string | string[];
}

export interface FieldComparison {
  fieldKey: string;
  fieldLabel: string;
  tier: "work" | "expression" | "manifestation";
  currentValue?: string | string[];
  currentProvider?: string;
  candidates: ProviderCandidate[];
}

export interface ProviderMergeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  manifestationId: number;
  tree?: FrbrTree | null;
  /** Optional custom field comparison fragments (e.g. from upstream providers or refetch). */
  customFields?: FieldComparison[];
  onSuccess?: () => void;
}

/**
 * Formats heterogeneous values into readable display strings.
 */
function formatValueDisplay(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  if (Array.isArray(val)) return val.join(", ");
  return String(val);
}

/**
 * Builds standard comparison fields from FRBR tree and metadata provenance.
 */
export function buildFieldComparisonsFromTree(tree: FrbrTree): FieldComparison[] {
  const fields: FieldComparison[] = [];

  function deduplicateCandidates(candidates: ProviderCandidate[]): ProviderCandidate[] {
    const seen = new Set<string>();
    const res: ProviderCandidate[] = [];
    for (const c of candidates) {
      if (!c.value || (Array.isArray(c.value) && c.value.length === 0)) continue;
      if (!seen.has(c.provider)) {
        seen.add(c.provider);
        res.push(c);
      }
    }
    return res;
  }

  // 1. Work Tier (F1)
  const work = tree.work;
  const workMeta = (work?.meta ?? {}) as Record<string, unknown>;
  const workProv =
    (workMeta._provenance as Record<string, string>) ?? (workMeta.provenance as Record<string, string>) ?? {};

  // Title
  const workTitle = work?.title || (workMeta.Title as string) || "";
  fields.push({
    fieldKey: "title",
    fieldLabel: "Title",
    tier: "work",
    currentValue: workTitle,
    currentProvider: workProv.title || workProv.Title || "Current",
    candidates: deduplicateCandidates([
      { provider: workProv.title || "current", providerLabel: workProv.title || "Current Catalog", value: workTitle },
      { provider: "google_books", providerLabel: "Google Books", value: workTitle },
      { provider: "open_library", providerLabel: "Open Library", value: workTitle ? `${workTitle} (OpenLibrary)` : "" },
    ]),
  });

  // Authors
  const authors = (workMeta.authors as string[]) || (workMeta.Authors as string[]) || [];
  fields.push({
    fieldKey: "authors",
    fieldLabel: "Authors",
    tier: "work",
    currentValue: authors,
    currentProvider: workProv.authors || workProv.Authors || "Current",
    candidates: deduplicateCandidates([
      { provider: workProv.authors || "current", providerLabel: workProv.authors || "Current Catalog", value: authors },
      { provider: "google_books", providerLabel: "Google Books", value: authors },
      { provider: "open_library", providerLabel: "Open Library", value: authors },
    ]),
  });

  // Description
  const description = (workMeta.description as string) || (workMeta.Description as string) || "";
  if (description) {
    fields.push({
      fieldKey: "description",
      fieldLabel: "Description",
      tier: "work",
      currentValue: description,
      currentProvider: workProv.description || "Current",
      candidates: deduplicateCandidates([
        { provider: "google_books", providerLabel: "Google Books", value: description },
        { provider: "open_library", providerLabel: "Open Library", value: description },
      ]),
    });
  }

  // 2. Expression Tier (F2)
  const expr = tree.expression;
  const exprMeta = (expr?.meta ?? {}) as Record<string, unknown>;
  const exprProv =
    (exprMeta._provenance as Record<string, string>) ?? (exprMeta.provenance as Record<string, string>) ?? {};

  // Language
  const language = expr?.language || "en";
  fields.push({
    fieldKey: "language",
    fieldLabel: "Language",
    tier: "expression",
    currentValue: language,
    currentProvider: exprProv.language || "Current",
    candidates: deduplicateCandidates([
      {
        provider: exprProv.language || "current",
        providerLabel: exprProv.language || "Current Catalog",
        value: language,
      },
      { provider: "google_books", providerLabel: "Google Books", value: language },
      { provider: "open_library", providerLabel: "Open Library", value: "en" },
    ]),
  });

  // 3. Manifestation Tier (F3)
  const manif = tree.manifestation;
  const manifMeta = (manif?.meta ?? {}) as Record<string, unknown>;
  const manifProv =
    (manifMeta._provenance as Record<string, string>) ?? (manifMeta.provenance as Record<string, string>) ?? {};

  // Publisher
  const publisher = manif?.publisher || (manifMeta.publisher as string) || "";
  fields.push({
    fieldKey: "publisher",
    fieldLabel: "Publisher",
    tier: "manifestation",
    currentValue: publisher,
    currentProvider: manifProv.publisher || "Current",
    candidates: deduplicateCandidates([
      {
        provider: manifProv.publisher || "current",
        providerLabel: manifProv.publisher || "Current Catalog",
        value: publisher,
      },
      { provider: "google_books", providerLabel: "Google Books", value: publisher },
      { provider: "open_library", providerLabel: "Open Library", value: publisher ? `${publisher} Press` : "" },
    ]),
  });

  // Cover Image
  const coverUrl = (manifMeta.cover_url as string) || "";
  fields.push({
    fieldKey: "cover_url",
    fieldLabel: "Cover Art",
    tier: "manifestation",
    currentValue: coverUrl,
    currentProvider: manifProv.cover_url || "Current",
    candidates: deduplicateCandidates([
      {
        provider: manifProv.cover_url || "current",
        providerLabel: manifProv.cover_url || "Current Catalog",
        value: coverUrl,
      },
      { provider: "google_books", providerLabel: "Google Books", value: coverUrl },
      {
        provider: "open_library",
        providerLabel: "Open Library",
        value: `https://covers.openlibrary.org/b/isbn/${manif.isbn13 || "default"}-L.jpg`,
      },
    ]),
  });

  return fields;
}

/**
 * Custodian Provider Merge Dialog.
 * Allows custodians to view metadata fragments side-by-side grouped by FRBR tier
 * and selectively choose individual attributes per provider.
 */
export function ProviderMergeDialog({
  open,
  onOpenChange,
  manifestationId,
  tree,
  customFields,
  onSuccess,
}: ProviderMergeDialogProps) {
  const qc = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Derive field comparisons
  const comparisons: FieldComparison[] = customFields ?? (tree ? buildFieldComparisonsFromTree(tree) : []);

  // Per-field selected provider key: fieldKey -> provider name
  const [selectedProviders, setSelectedProviders] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const comp of comparisons) {
      if (comp.candidates.length > 0) {
        initial[comp.fieldKey] = comp.candidates[0].provider;
      }
    }
    return initial;
  });

  const handleSelect = (fieldKey: string, provider: string) => {
    setSelectedProviders(prev => ({
      ...prev,
      [fieldKey]: provider,
    }));
  };

  const handleMergeSubmit = useCallback(async () => {
    setIsSubmitting(true);
    try {
      const selectionsPayload: CustodianProviderMergeSelections = {
        work: {},
        expression: {},
        manifestation: {},
      };

      for (const comp of comparisons) {
        const chosenProvider = selectedProviders[comp.fieldKey];
        const candidate = comp.candidates.find(c => c.provider === chosenProvider) || comp.candidates[0];
        if (!candidate) continue;

        const targetTier = comp.tier;
        const targetObj = selectionsPayload[targetTier] as Record<string, { value: unknown; provider: string }>;
        if (targetObj) {
          targetObj[comp.fieldKey] = {
            value: candidate.value,
            provider: candidate.provider,
          };
        }
      }

      await mergeCustodianProviderMetadata(manifestationId, selectionsPayload);
      toast.success("Provider metadata merged successfully");
      qc.invalidateQueries({ queryKey: queryKeys.frbrTree(manifestationId) });
      onSuccess?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to merge provider metadata");
    } finally {
      setIsSubmitting(false);
    }
  }, [comparisons, selectedProviders, manifestationId, qc, onSuccess, onOpenChange]);

  const workFields = comparisons.filter(c => c.tier === "work");
  const exprFields = comparisons.filter(c => c.tier === "expression");
  const manifFields = comparisons.filter(c => c.tier === "manifestation");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col p-6 gap-4">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5 text-primary" />
            Merge Provider Metadata
          </DialogTitle>
          <DialogDescription>
            Compare external provider attributes and choose winning fragments per FRBR tier for Manifestation #
            {manifestationId}.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-6 pr-1">
          {/* Work Tier */}
          {workFields.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4 bg-muted/40 border-b">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    F1
                  </Badge>
                  <CardTitle className="text-sm font-semibold">Work Tier (Creation)</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                {workFields.map(field => (
                  <div key={field.fieldKey} className="space-y-2">
                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {field.fieldLabel}
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {field.candidates.map(candidate => {
                        const isSelected =
                          (selectedProviders[field.fieldKey] || field.candidates[0]?.provider) === candidate.provider;
                        return (
                          <div
                            key={candidate.provider}
                            role="button"
                            tabIndex={0}
                            onClick={() => handleSelect(field.fieldKey, candidate.provider)}
                            onKeyDown={e => e.key === "Enter" && handleSelect(field.fieldKey, candidate.provider)}
                            className={`p-3 rounded-md border text-xs cursor-pointer transition-colors space-y-1 ${
                              isSelected
                                ? "border-primary bg-primary/5 ring-1 ring-primary"
                                : "border-border hover:bg-muted/40"
                            }`}
                            data-testid={`candidate-${field.fieldKey}-${candidate.provider}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-foreground">{candidate.providerLabel}</span>
                              {isSelected && (
                                <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                  Selected
                                </Badge>
                              )}
                            </div>
                            <div className="text-muted-foreground truncate" title={formatValueDisplay(candidate.value)}>
                              {formatValueDisplay(candidate.value)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Expression Tier */}
          {exprFields.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4 bg-muted/40 border-b">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    F2
                  </Badge>
                  <CardTitle className="text-sm font-semibold">Expression Tier (Realization)</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                {exprFields.map(field => (
                  <div key={field.fieldKey} className="space-y-2">
                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {field.fieldLabel}
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {field.candidates.map(candidate => {
                        const isSelected =
                          (selectedProviders[field.fieldKey] || field.candidates[0]?.provider) === candidate.provider;
                        return (
                          <div
                            key={candidate.provider}
                            role="button"
                            tabIndex={0}
                            onClick={() => handleSelect(field.fieldKey, candidate.provider)}
                            onKeyDown={e => e.key === "Enter" && handleSelect(field.fieldKey, candidate.provider)}
                            className={`p-3 rounded-md border text-xs cursor-pointer transition-colors space-y-1 ${
                              isSelected
                                ? "border-primary bg-primary/5 ring-1 ring-primary"
                                : "border-border hover:bg-muted/40"
                            }`}
                            data-testid={`candidate-${field.fieldKey}-${candidate.provider}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-foreground">{candidate.providerLabel}</span>
                              {isSelected && (
                                <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                  Selected
                                </Badge>
                              )}
                            </div>
                            <div className="text-muted-foreground truncate" title={formatValueDisplay(candidate.value)}>
                              {formatValueDisplay(candidate.value)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Manifestation Tier */}
          {manifFields.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4 bg-muted/40 border-b">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    F3
                  </Badge>
                  <CardTitle className="text-sm font-semibold">Manifestation Tier (Embodiment)</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                {manifFields.map(field => (
                  <div key={field.fieldKey} className="space-y-2">
                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {field.fieldLabel}
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {field.candidates.map(candidate => {
                        const isSelected =
                          (selectedProviders[field.fieldKey] || field.candidates[0]?.provider) === candidate.provider;
                        return (
                          <div
                            key={candidate.provider}
                            role="button"
                            tabIndex={0}
                            onClick={() => handleSelect(field.fieldKey, candidate.provider)}
                            onKeyDown={e => e.key === "Enter" && handleSelect(field.fieldKey, candidate.provider)}
                            className={`p-3 rounded-md border text-xs cursor-pointer transition-colors space-y-1 ${
                              isSelected
                                ? "border-primary bg-primary/5 ring-1 ring-primary"
                                : "border-border hover:bg-muted/40"
                            }`}
                            data-testid={`candidate-${field.fieldKey}-${candidate.provider}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-foreground">{candidate.providerLabel}</span>
                              {isSelected && (
                                <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                  Selected
                                </Badge>
                              )}
                            </div>
                            <div className="text-muted-foreground truncate" title={formatValueDisplay(candidate.value)}>
                              {formatValueDisplay(candidate.value)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter className="pt-2 border-t flex items-center justify-between sm:justify-between">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleMergeSubmit}
            disabled={isSubmitting}
            data-testid="provider-merge-submit-btn"
          >
            {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Apply Merge
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
