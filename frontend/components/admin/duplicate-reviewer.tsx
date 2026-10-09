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

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CopyCheck, Loader2, RefreshCw, X } from "lucide-react";
import { toast } from "sonner";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  dismissDuplicateCandidate,
  DuplicateCandidate,
  DuplicateSide,
  getDuplicateCandidates,
  mergeDuplicateCandidate,
  runDuplicateScan,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

/** Props for the DuplicateReviewer component. */
interface DuplicateReviewerProps {
  /** Whether the viewer may merge and dismiss candidates. */
  canEdit: boolean;
}

/** Confidence at or above which a badge is rendered as high confidence. */
const HIGH_CONFIDENCE = 0.9;

/**
 * Render a candidate's decision, labelled by the stage that made it.
 *
 * A classifier verdict is categorical, not probabilistic: the pair was queued
 * because two records share an edition identifier, or an identical title with a
 * shared author. Showing that as a percentage would present a rule as a
 * calibrated belief, so it is labelled as a match and carries no number.
 *
 * @param props - The component props
 * @param props.candidate - The candidate whose decision to render
 * @returns {JSX.Element} A badge naming the provenance of the decision
 */
function ConfidenceBadge({ candidate }: { candidate: DuplicateCandidate }) {
  if (candidate.resolution_source === "heuristic" || candidate.confidence === null) {
    return (
      <Badge variant="default" data-testid="confidence-badge" data-provenance="heuristic">
        match (rules)
      </Badge>
    );
  }

  const percent = Math.round(candidate.confidence * 100);
  const variant = candidate.confidence >= HIGH_CONFIDENCE ? "destructive" : "secondary";
  return (
    <Badge variant={variant} data-testid="confidence-badge" data-provenance="llama">
      LLM {percent}% match
    </Badge>
  );
}

/**
 * Render one side of a candidate pair in the comparison table.
 *
 * The `tier` discriminator on the payload selects which field set is shown, so
 * ISBN-family identifiers are only ever read from a Manifestation side.
 *
 * @param props - The component props
 * @param props.side - The serialized entity, or null when it no longer exists
 * @param props.sideLabel - Column heading, "A" or "B"
 * @param props.isPrimary - Whether this side is the currently selected primary
 * @param props.onSelectPrimary - Callback invoked when this side is chosen as primary
 * @returns {JSX.Element} The comparison column
 */
function SidePanel({
  side,
  sideLabel,
  isPrimary,
  onSelectPrimary,
}: {
  side: DuplicateSide | null;
  sideLabel: string;
  isPrimary: boolean;
  onSelectPrimary: () => void;
}) {
  if (!side) {
    return (
      <div className="flex-1 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        Entity no longer exists
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex-1 rounded-lg border p-4 transition-colors",
        isPrimary ? "border-primary bg-primary/5" : "border-border"
      )}
      data-testid={`duplicate-side-${sideLabel}`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Entity {sideLabel}</span>
        {isPrimary && <Badge>Primary</Badge>}
      </div>

      <h3 className="mb-1 font-medium">
        {side.tier === "expression" ? side.label || "Untitled" : side.title || "Untitled"}
      </h3>
      <p className="mb-3 text-xs text-muted-foreground">ID {side.id}</p>

      <dl className="space-y-2 text-sm">
        {side.tier === "manifestation" ? (
          <>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">ISBN-13</dt>
              <dd className="font-mono">{side.isbn13 ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Format</dt>
              <dd>{side.format ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Publisher</dt>
              <dd>{side.publisher ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Published</dt>
              <dd>{side.publication_date ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Items</dt>
              <dd>{side.item_count}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Catalog no.</dt>
              <dd>{side.catalog_number ?? "—"}</dd>
            </div>
            {side.cover_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={side.cover_url} alt={`Cover for ${side.title}`} className="mt-2 h-24 w-auto rounded" />
            )}
          </>
        ) : side.tier === "expression" ? (
          <>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Language</dt>
              <dd>{side.language ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Content type</dt>
              <dd>{side.content_type ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Manifestations</dt>
              <dd>{side.manifestation_count}</dd>
            </div>
            {side.cover_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={side.cover_url}
                alt={`Cover for ${side.label || "expression"}`}
                className="mt-2 h-24 w-auto rounded"
              />
            )}
          </>
        ) : (
          <>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Sort title</dt>
              <dd>{side.sort_title ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Genres</dt>
              <dd>{side.genres ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Expressions</dt>
              <dd>{side.expression_count}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-muted-foreground">Description</dt>
              <dd>{side.description_present ? "Present" : "None"}</dd>
            </div>
          </>
        )}
      </dl>

      <div className="mt-4 border-t pt-3">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Creators</p>
        {side.creators.length > 0 ? (
          <ul className="space-y-0.5 text-sm">
            {side.creators.map(creator => (
              <li key={creator}>{creator}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">None recorded</p>
        )}
      </div>

      <Button
        variant={isPrimary ? "default" : "outline"}
        size="sm"
        className="mt-4 w-full"
        onClick={onSelectPrimary}
        disabled={isPrimary}
      >
        {isPrimary ? "Primary selected" : "Keep this one"}
      </Button>
    </div>
  );
}

/**
 * Side-by-side duplicate review queue.
 *
 * Each candidate is compared field by field, and the administrator picks which
 * entity survives.  Merging is destructive and irreversible, so it is always
 * confirmed first; dismissing records the decision so the pair is never
 * re-queued by a later detection run.
 *
 * @param props - The component props
 * @param props.canEdit - Whether the viewer may merge and dismiss candidates
 * @returns {JSX.Element} The duplicate review queue
 */
export function DuplicateReviewer({ canEdit }: DuplicateReviewerProps) {
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pendingMerge, setPendingMerge] = useState<{ candidate: DuplicateCandidate; primaryId: number } | null>(null);

  const limit = 10;
  const pages = Math.max(1, Math.ceil(total / limit));

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await getDuplicateCandidates({ status: "pending", page, limit });
      setCandidates(res.data);
      setTotal(res.meta.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load duplicate candidates");
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const report = await runDuplicateScan({ tier: "all" });
      toast.success(`Scan queued ${report.created} new candidate(s)`);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Duplicate scan failed");
    } finally {
      setIsScanning(false);
    }
  };

  const handleDismiss = async (candidate: DuplicateCandidate) => {
    setBusyId(candidate.id);
    try {
      await dismissDuplicateCandidate(candidate.id);
      toast.success("Candidate dismissed");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to dismiss candidate");
    } finally {
      setBusyId(null);
    }
  };

  const confirmMerge = async () => {
    if (!pendingMerge) return;
    const { candidate, primaryId } = pendingMerge;
    setPendingMerge(null);
    setBusyId(candidate.id);
    try {
      const result = await mergeDuplicateCandidate(candidate.id, primaryId);
      toast.success(`Merged into entity ${result.primary_id}`);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Merge failed and was rolled back");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground" data-testid="duplicate-total">
          {total} candidate{total === 1 ? "" : "s"} awaiting review
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={isLoading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
          {canEdit && (
            <Button size="sm" onClick={() => void handleScan()} disabled={isScanning}>
              {isScanning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CopyCheck className="mr-2 h-4 w-4" />}
              Run scan
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : candidates.length === 0 ? (
        <EmptyState
          title="No duplicate candidates"
          description="Run a scan to compare the catalog for duplicate Works and Manifestations. A scan resolves what it can from the records alone and needs no language model; use the CLI with --engine llama to adjudicate the remaining grey zone."
          icon={CopyCheck}
        />
      ) : (
        <ul className="flex flex-col gap-6">
          {candidates.map(candidate => (
            <li
              key={candidate.id}
              className="rounded-lg border p-4"
              data-testid={`duplicate-candidate-${candidate.id}`}
            >
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{candidate.entity_tier}</Badge>
                  <ConfidenceBadge candidate={candidate} />
                </div>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void handleDismiss(candidate)}
                    disabled={busyId === candidate.id}
                  >
                    <X className="mr-2 h-4 w-4" />
                    Not duplicates
                  </Button>
                )}
              </div>

              {candidate.llm_reasoning && (
                <p className="mb-4 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
                  {candidate.llm_reasoning}
                </p>
              )}

              <DuplicateComparison
                candidate={candidate}
                canEdit={canEdit}
                onRequestMerge={(target, primaryId) => setPendingMerge({ candidate: target, primaryId })}
              />
            </li>
          ))}
        </ul>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.min(pages, p + 1))}
            disabled={page >= pages}
          >
            Next
          </Button>
        </div>
      )}

      <AlertDialog open={pendingMerge !== null} onOpenChange={open => !open && setPendingMerge(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Merge these entities?</AlertDialogTitle>
            <AlertDialogDescription>
              <span className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                <span>
                  This permanently deletes one entity and re-parents its children onto the other. It cannot be undone,
                  and the decision is recorded in the entity audit log.
                </span>
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmMerge()}>Merge permanently</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/**
 * Comparison table for a single candidate, with primary-entity selection.
 *
 * @param props - The component props
 * @param props.candidate - The candidate to compare
 * @param props.canEdit - Whether the viewer may choose a primary
 * @param props.onRequestMerge - Called with the candidate and chosen primary id
 * @returns {JSX.Element} The comparison table
 */
function DuplicateComparison({
  candidate,
  canEdit,
  onRequestMerge,
}: {
  candidate: DuplicateCandidate;
  canEdit: boolean;
  onRequestMerge: (candidate: DuplicateCandidate, primaryId: number) => void;
}) {
  const [primaryId, setPrimaryId] = useState<number>(candidate.source_id);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <SidePanel
          side={candidate.source}
          sideLabel="A"
          isPrimary={primaryId === candidate.source_id}
          onSelectPrimary={() => setPrimaryId(candidate.source_id)}
        />
        <SidePanel
          side={candidate.target}
          sideLabel="B"
          isPrimary={primaryId === candidate.target_id}
          onSelectPrimary={() => setPrimaryId(candidate.target_id)}
        />
      </div>
      {canEdit && (
        <Button
          className="self-end"
          onClick={() => onRequestMerge(candidate, primaryId)}
          disabled={!candidate.source || !candidate.target}
        >
          Merge keeping entity {primaryId}
        </Button>
      )}
    </div>
  );
}
