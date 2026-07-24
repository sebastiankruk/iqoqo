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
import { Check, X, ClipboardCopy, Loader2, MessageSquare, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useEscalationQueue, useResolveEscalation, useResolvedEscalations } from "@/lib/api/escalations";
import { getTargetLabel, getAdminTargetHref } from "@/lib/escalation-utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { EscalationRequest } from "@/types/frbr";

/** Format ISO date string to a readable locale string.
 *
 * @param iso - The ISO date string.
 * @returns The formatted date string.
 */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/**
 * Resolve dialog or inline form per queue item.
 *
 * @param root0 - The props object.
 * @param root0.request - The escalation request to resolve.
 * @returns Resolve action buttons or inline form.
 */
function ResolveActions({ request: esc }: { request: EscalationRequest }) {
  const [activeAction, setActiveAction] = useState<"accepted" | "rejected" | "duplicate" | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");
  const resolveMutation = useResolveEscalation();
  const t = useTranslations("HelpRequests");

  const handleResolve = (status: "accepted" | "rejected" | "duplicate") => {
    resolveMutation.mutate(
      {
        escalationId: esc.id,
        data: {
          status,
          resolution_note: resolutionNote.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          const statusMessages: Record<string, string> = {
            accepted: t("requestAccepted"),
            rejected: t("requestRejected"),
            duplicate: t("requestDuplicate"),
          };
          toast.success(statusMessages[status] || `Request ${status}`);
          setActiveAction(null);
          setResolutionNote("");
        },
        onError: err => {
          toast.error(err instanceof Error ? err.message : t("failedToResolve"));
        },
      }
    );
  };

  if (!activeAction) {
    return (
      <div className="flex gap-1.5" data-testid="resolve-buttons">
        <Button
          size="sm"
          variant="outline"
          className="gap-1 text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950"
          onClick={() => setActiveAction("accepted")}
          disabled={resolveMutation.isPending}
        >
          <Check className="h-3.5 w-3.5" />
          {t("accept")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1 text-destructive border-destructive/20 hover:bg-destructive/10"
          onClick={() => setActiveAction("rejected")}
          disabled={resolveMutation.isPending}
        >
          <X className="h-3.5 w-3.5" />
          {t("reject")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1 text-amber-600 border-amber-200 hover:bg-amber-50 dark:hover:bg-amber-950"
          onClick={() => setActiveAction("duplicate")}
          disabled={resolveMutation.isPending}
        >
          <ClipboardCopy className="h-3.5 w-3.5" />
          {t("markAsDuplicate")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 mt-2 w-full">
      <textarea
        placeholder={t("resolutionNoteOptional")}
        value={resolutionNote}
        onChange={e => setResolutionNote(e.target.value)}
        rows={2}
        className="flex min-h-[40px] w-full rounded-md border border-input bg-transparent px-2 py-1 text-xs shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      />
      <div className="flex gap-1.5">
        <Button
          size="sm"
          variant={activeAction === "accepted" ? "default" : "outline"}
          onClick={() => handleResolve(activeAction!)}
          disabled={resolveMutation.isPending}
        >
          {resolveMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("confirm")}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setActiveAction(null)} disabled={resolveMutation.isPending}>
          {t("cancel")}
        </Button>
      </div>
    </div>
  );
}

/**
 * Loading skeleton for the escalation queue.
 *
 * @returns The loading skeleton JSX element.
 */
function QueueSkeleton() {
  return (
    <div className="space-y-4" data-testid="escalation-queue-loading">
      {[1, 2, 3].map(i => (
        <Card key={i}>
          <CardContent className="p-4 space-y-2">
            <div className="h-4 w-48 animate-pulse rounded bg-muted" />
            <div className="h-3 w-64 animate-pulse rounded bg-muted" />
            <div className="h-3 w-32 animate-pulse rounded bg-muted" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Empty state placeholder when no escalations are pending.
 *
 * @returns The empty state JSX element.
 */
function QueueEmpty() {
  const t = useTranslations("HelpRequests");
  return (
    <div
      data-testid="escalation-queue-empty"
      className="flex flex-col items-center justify-center py-16 text-muted-foreground"
    >
      <MessageSquare className="h-12 w-12 mb-4 opacity-30" />
      <p className="text-sm font-medium">{t("noPendingUserRequests")}</p>
      <p className="text-xs mt-1">{t("newRequestsAppear")}</p>
    </div>
  );
}

/**
 * Render status badge for a resolved escalation.
 *
 * @param props - Component props.
 * @param props.status - The resolved status.
 * @returns Status badge JSX element.
 */
function ResolvedStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "accepted":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
          <Check className="h-3 w-3" />
          Accepted
        </span>
      );
    case "rejected":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive bg-destructive/10 px-2 py-0.5 rounded-full border border-destructive/20">
          <X className="h-3 w-3" />
          Rejected
        </span>
      );
    case "duplicate":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
          <ClipboardCopy className="h-3 w-3" />
          Duplicate
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full border">
          {status}
        </span>
      );
  }
}

/**
 * Resolved (processed) requests section with toggle.
 *
 * @returns The processed requests JSX element.
 */
function ProcessedRequestsSection() {
  const [isOpen, setIsOpen] = useState(false);
  const { data: resolved, isLoading, isError, error } = useResolvedEscalations(isOpen);
  const t = useTranslations("HelpRequests");

  return (
    <div className="mt-6 border-t border-border pt-4">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground px-2"
      >
        {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        <span>{t("processedRequests")}</span>
      </Button>

      {isOpen && (
        <div className="mt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
          {isLoading && (
            <div className="space-y-3">
              {[1, 2].map(i => (
                <Card key={i}>
                  <CardContent className="p-3 space-y-2">
                    <div className="h-3 w-32 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-48 animate-pulse rounded bg-muted" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {isError && (
            <Card>
              <CardContent className="p-3 text-destructive text-xs">
                {t("failedToLoadProcessed")}: {error instanceof Error ? error.message : "Unknown error"}
              </CardContent>
            </Card>
          )}

          {resolved && resolved.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground text-center">
              <Check className="h-8 w-8 mb-2 opacity-30" />
              <p className="text-xs">{t("noProcessedRequests")}</p>
            </div>
          )}

          {resolved?.map(esc => (
            <Card key={esc.id}>
              <CardContent className="p-3 space-y-2 text-xs">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm">
                        {esc.user_display_name || esc.user_username || "Anonymous"}
                      </span>
                      <ResolvedStatusBadge status={esc.status} />
                      {(() => {
                        const href = getAdminTargetHref(esc);
                        return href ? (
                          <Link
                            href={href}
                            className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded hover:underline hover:text-foreground transition-colors"
                          >
                            {getTargetLabel(esc)}
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        ) : (
                          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {getTargetLabel(esc)}
                          </span>
                        );
                      })()}
                    </div>
                    <div className="flex items-baseline gap-2 text-xs">
                      <span className="font-mono font-medium text-muted-foreground uppercase text-[10px]">
                        {esc.field_name}
                      </span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-mono text-foreground">{esc.suggested_value}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0 flex flex-col items-end gap-0.5">
                    {esc.resolved_at && (
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        {formatDate(esc.resolved_at)}
                      </span>
                    )}
                    {(esc.resolver_display_name || esc.resolved_by) && (
                      <span className="text-[10px] text-muted-foreground">
                        {t("resolvedBy", { name: esc.resolver_display_name || "Custodian" })}
                      </span>
                    )}
                  </div>
                </div>
                {esc.resolution_note && (
                  <div className="rounded bg-muted/50 p-2 text-[11px] italic text-muted-foreground border-l-2 border-primary/50">
                    {esc.resolution_note}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Escalation queue component for custodian review.
 *
 * Fetches pending escalation requests and renders them in a card-based list.
 * Each card shows requester info, target entity, field name, suggested value,
 * note, and timestamp. Custodians can accept, reject, or mark as duplicate
 * with an optional resolution note.
 *
 * @returns The escalation queue JSX element.
 */
export function EscalationQueue() {
  const { data: queue, isLoading, isError, error } = useEscalationQueue();
  const t = useTranslations("HelpRequests");

  if (isLoading) return <QueueSkeleton />;
  if (isError) {
    return (
      <Card>
        <CardContent className="p-4 text-destructive">
          <p>
            {t("failedToLoad")}: {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!queue || queue.length === 0) {
    return (
      <div data-testid="escalation-queue">
        <QueueEmpty />
        <ProcessedRequestsSection />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="escalation-queue">
      {queue.map(esc => (
        <Card key={esc.id}>
          <CardContent className="p-4 space-y-3">
            {/* Requester and target info */}
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold">
                    {esc.user_display_name || esc.user_username || "Anonymous"}
                  </span>
                  {(() => {
                    const href = getAdminTargetHref(esc);
                    return href ? (
                      <Link
                        href={href}
                        className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded hover:underline hover:text-foreground transition-colors"
                      >
                        {getTargetLabel(esc)}
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    ) : (
                      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                        {getTargetLabel(esc)}
                      </span>
                    );
                  })()}
                </div>
                <div className="flex items-baseline gap-2 text-xs">
                  <span className="font-mono font-semibold text-primary">{esc.field_name}</span>
                  <span className="text-muted-foreground">→</span>
                  <span className="font-mono text-foreground">{esc.suggested_value}</span>
                </div>
                {esc.current_value && (
                  <p className="text-xs text-muted-foreground">
                    <span className="line-through">{esc.current_value}</span>
                  </p>
                )}
              </div>
              <span className="text-[10px] text-muted-foreground whitespace-nowrap shrink-0 tabular-nums">
                {esc.created_at ? formatDate(esc.created_at) : ""}
              </span>
            </div>

            {/* Note */}
            {esc.note && (
              <p className="text-xs text-muted-foreground bg-muted/50 rounded p-2 italic border-l-2 border-primary/50">
                {esc.note}
              </p>
            )}

            {/* Resolve actions */}
            <ResolveActions request={esc} />
          </CardContent>
        </Card>
      ))}
      <ProcessedRequestsSection />
    </div>
  );
}
