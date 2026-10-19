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

import { useState, useCallback, useMemo } from "react";
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
 *
 * @param val - The raw value.
 * @returns Human-readable string representation.
 */
function formatValueDisplay(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  if (Array.isArray(val)) return val.join(", ");
  return String(val);
}

/**
 * Filter out empty candidates and duplicate provider keys.
 *
 * @param candidates - List of candidate provider fragments.
 * @returns Deduplicated list of candidates.
 */
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

/**
 * Returns a human-readable label for a provider key.
 */
export function getProviderLabel(provider: string): string {
  if (provider.toLowerCase().startsWith("federation:")) {
    return `Federation (${provider.slice(11)})`;
  }
  switch (provider.toLowerCase()) {
    case "google_books":
      return "Google Books";
    case "open_library":
      return "Open Library";
    case "allegro":
      return "Allegro";
    case "discogs":
      return "Discogs";
    case "musicbrainz":
      return "MusicBrainz";
    case "tmdb":
      return "TMDB";
    case "current":
      return "Current Catalog";
    default:
      return provider.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()) || "Current Catalog";
  }
}

/**
 * Helper to extract a field value from provider-specific raw payload structures.
 */
function extractProviderField(providerData: unknown, fieldKey: string): string | string[] | undefined {
  if (!providerData || typeof providerData !== "object") return undefined;
  const pData = providerData as Record<string, unknown>;
  const volumeInfo = (pData.volumeInfo && typeof pData.volumeInfo === "object" ? pData.volumeInfo : undefined) as
    | Record<string, unknown>
    | undefined;

  switch (fieldKey) {
    case "title":
      return (
        (typeof pData.title === "string" ? pData.title : undefined) ||
        (typeof volumeInfo?.title === "string" ? volumeInfo.title : undefined)
      );
    case "authors": {
      const val = pData.authors || volumeInfo?.authors;
      if (Array.isArray(val)) return val.map(String);
      if (typeof val === "string" && val.trim()) return [val.trim()];
      return undefined;
    }
    case "description": {
      const val = pData.description || volumeInfo?.description;
      return typeof val === "string" ? val : undefined;
    }
    case "language":
      return (
        (typeof pData.language === "string" ? pData.language : undefined) ||
        (typeof volumeInfo?.language === "string" ? volumeInfo.language : undefined)
      );
    case "publisher": {
      const publishers = Array.isArray(pData.publishers) ? pData.publishers : undefined;
      const val = pData.publisher || publishers?.[0] || volumeInfo?.publisher;
      return typeof val === "string" ? val : undefined;
    }
    case "cover_url": {
      const imageLinks = (
        volumeInfo?.imageLinks && typeof volumeInfo.imageLinks === "object" ? volumeInfo.imageLinks : undefined
      ) as Record<string, unknown> | undefined;
      const val = pData.cover_url || pData.cover || pData.thumbnail || imageLinks?.thumbnail;
      return typeof val === "string" ? val : undefined;
    }
    case "page_count": {
      const val = pData.page_count ?? pData.pageCount ?? volumeInfo?.pageCount;
      return val != null ? String(val) : undefined;
    }
    default: {
      const val = pData[fieldKey];
      if (typeof val === "string") return val;
      if (Array.isArray(val)) return val.map(String);
      return undefined;
    }
  }
}

/**
 * Builds standard comparison fields from FRBR tree and metadata provenance.
 * Extracts authentic candidate values from provider payloads and entity provenance
 * without fabricating synthetic strings.
 *
 * @param tree - The FRBR hierarchy tree.
 * @returns Array of field comparisons across tiers.
 */
export function buildFieldComparisonsFromTree(tree: FrbrTree): FieldComparison[] {
  const fields: FieldComparison[] = [];

  const manif = tree.manifestation;
  const manifMeta = (manif?.meta ?? {}) as Record<string, unknown>;
  const manifProv =
    (manifMeta._provenance as Record<string, string>) ?? (manifMeta.provenance as Record<string, string>) ?? {};

  const manifObj = manif as unknown as (Record<string, unknown> & { raw_payload?: unknown }) | null | undefined;
  const workObj = tree.work as unknown as (Record<string, unknown> & { raw_payload?: unknown }) | null | undefined;
  const workMeta = (tree.work?.meta ?? {}) as Record<string, unknown>;

  const rawPayload = (manifObj?.raw_payload ??
    manifMeta.raw_payload ??
    workObj?.raw_payload ??
    workMeta.raw_payload ??
    {}) as Record<string, unknown>;

  // Known external provider keys in raw_payload
  const providerKeys = new Set<string>();
  for (const k of Object.keys(rawPayload)) {
    if (typeof rawPayload[k] === "object" && rawPayload[k] !== null) {
      providerKeys.add(k);
    }
  }

  // 1. Work Tier (F1)
  const work = tree.work;
  const workProv =
    (workMeta._provenance as Record<string, string>) ?? (workMeta.provenance as Record<string, string>) ?? {};

  // Title
  const workTitle = work?.title || (workMeta.Title as string) || "";
  const titleProv = workProv.title || workProv.Title || "current";
  const titleCandidates: ProviderCandidate[] = [
    { provider: titleProv, providerLabel: getProviderLabel(titleProv), value: workTitle },
  ];
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "title");
    if (val) {
      titleCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  fields.push({
    fieldKey: "title",
    fieldLabel: "Title",
    tier: "work",
    currentValue: workTitle,
    currentProvider: titleProv,
    candidates: deduplicateCandidates(titleCandidates),
  });

  // Authors
  const authors = (workMeta.authors as string[]) || (workMeta.Authors as string[]) || [];
  const authorsProv = workProv.authors || workProv.Authors || "current";
  const authorsCandidates: ProviderCandidate[] = [
    { provider: authorsProv, providerLabel: getProviderLabel(authorsProv), value: authors },
  ];
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "authors");
    if (val && Array.isArray(val) && val.length > 0) {
      authorsCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  fields.push({
    fieldKey: "authors",
    fieldLabel: "Authors",
    tier: "work",
    currentValue: authors,
    currentProvider: authorsProv,
    candidates: deduplicateCandidates(authorsCandidates),
  });

  // Description
  const description = (workMeta.description as string) || (workMeta.Description as string) || "";
  const descProv = workProv.description || "current";
  const descCandidates: ProviderCandidate[] = [
    { provider: descProv, providerLabel: getProviderLabel(descProv), value: description },
  ];
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "description");
    if (val) {
      descCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  const deduppedDesc = deduplicateCandidates(descCandidates);
  if (deduppedDesc.length > 0 && description) {
    fields.push({
      fieldKey: "description",
      fieldLabel: "Description",
      tier: "work",
      currentValue: description,
      currentProvider: descProv,
      candidates: deduppedDesc,
    });
  }

  // 2. Expression Tier (F2)
  const expr = tree.expression;
  const exprMeta = (expr?.meta ?? {}) as Record<string, unknown>;
  const exprProv =
    (exprMeta._provenance as Record<string, string>) ?? (exprMeta.provenance as Record<string, string>) ?? {};

  // Language
  const language = expr?.language || "en";
  const langProv = exprProv.language || "current";
  const langCandidates: ProviderCandidate[] = [
    { provider: langProv, providerLabel: getProviderLabel(langProv), value: language },
  ];
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "language");
    if (val) {
      langCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  fields.push({
    fieldKey: "language",
    fieldLabel: "Language",
    tier: "expression",
    currentValue: language,
    currentProvider: langProv,
    candidates: deduplicateCandidates(langCandidates),
  });

  // 3. Manifestation Tier (F3)
  // Publisher
  const publisher = manif?.publisher || (manifMeta.publisher as string) || "";
  const pubProv = manifProv.publisher || "current";
  const pubCandidates: ProviderCandidate[] = [
    { provider: pubProv, providerLabel: getProviderLabel(pubProv), value: publisher },
  ];
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "publisher");
    if (val) {
      pubCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  fields.push({
    fieldKey: "publisher",
    fieldLabel: "Publisher",
    tier: "manifestation",
    currentValue: publisher,
    currentProvider: pubProv,
    candidates: deduplicateCandidates(pubCandidates),
  });

  // Cover Image
  const coverUrl =
    (manifMeta.cover_url as string) ||
    ((manif as unknown as { cover_url?: string } | null | undefined)?.cover_url ?? "");
  const coverProv = manifProv.cover_url || "current";
  const coverCandidates: ProviderCandidate[] = [];
  if (coverUrl) {
    coverCandidates.push({
      provider: coverProv,
      providerLabel: getProviderLabel(coverProv),
      value: coverUrl,
    });
  }
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "cover_url");
    if (val && typeof val === "string") {
      coverCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  if (manif?.isbn13 && manif.isbn13.length >= 10 && !coverCandidates.some(c => c.provider === "open_library")) {
    coverCandidates.push({
      provider: "open_library",
      providerLabel: "Open Library",
      value: `https://covers.openlibrary.org/b/isbn/${manif.isbn13}-L.jpg`,
    });
  }
  if (coverCandidates.length > 0) {
    fields.push({
      fieldKey: "cover_url",
      fieldLabel: "Cover Art",
      tier: "manifestation",
      currentValue: coverUrl,
      currentProvider: coverProv,
      candidates: deduplicateCandidates(coverCandidates),
    });
  }

  // Page Count
  const rawPageCount =
    (manifMeta.page_count as string | number | undefined) ??
    (manif as unknown as { page_count?: string | number } | null | undefined)?.page_count;
  const pageCount = rawPageCount != null ? String(rawPageCount) : "";
  const pageProv = manifProv.page_count || "current";
  const pageCandidates: ProviderCandidate[] = [];
  if (pageCount) {
    pageCandidates.push({
      provider: pageProv,
      providerLabel: getProviderLabel(pageProv),
      value: pageCount,
    });
  }
  for (const pKey of providerKeys) {
    const val = extractProviderField(rawPayload[pKey], "page_count");
    if (val && typeof val === "string") {
      pageCandidates.push({ provider: pKey, providerLabel: getProviderLabel(pKey), value: val });
    }
  }
  if (pageCandidates.length > 0) {
    fields.push({
      fieldKey: "page_count",
      fieldLabel: "Page Count",
      tier: "manifestation",
      currentValue: pageCount,
      currentProvider: pageProv,
      candidates: deduplicateCandidates(pageCandidates),
    });
  }

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
  const comparisons: FieldComparison[] = useMemo(() => {
    return customFields ?? (tree ? buildFieldComparisonsFromTree(tree) : []);
  }, [customFields, tree]);

  // Per-field selected provider key: fieldKey -> provider name (defaults to first candidate)
  const [selectedProviders, setSelectedProviders] = useState<Record<string, string>>({});

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
        const chosenProvider = selectedProviders[comp.fieldKey] || comp.candidates[0]?.provider;
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
