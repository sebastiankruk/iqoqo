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

import Link from "next/link";
import { CheckCircle2, XCircle, AlertCircle, Clock, HelpCircle, ExternalLink, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMyEscalations } from "@/lib/api/escalations";
import { getTargetHref, getTargetLabel } from "@/lib/escalation-utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Format ISO date string to readable locale format.
 *
 * @param iso - ISO date string.
 * @returns Formatted date string.
 */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * Render badge for escalation request type (Correction vs Deletion).
 *
 * @param props - Component props.
 * @param props.type - The request type string.
 * @returns Request type badge JSX element.
 */
function RequestTypeBadge({ type }: { type?: "correction" | "deletion" | string }) {
  const t = useTranslations("HelpRequests");
  if (type === "deletion") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-destructive bg-destructive/10 px-1.5 py-0.5 rounded border border-destructive/20">
        <Trash2 className="h-3 w-3" />
        {t("deletion")}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
      {t("correction")}
    </span>
  );
}

/**
 * Render status badge icon and label.
 *
 * @param props - Component props.
 * @param props.status - Escalation status.
 * @returns Status badge JSX element.
 */
function StatusBadge({ status }: { status: string }) {
  const t = useTranslations("HelpRequests");
  switch (status) {
    case "accepted":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="h-3 w-3" />
          {t("accepted")}
        </span>
      );
    case "rejected":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive bg-destructive/10 px-2 py-0.5 rounded-full border border-destructive/20">
          <XCircle className="h-3 w-3" />
          {t("rejected")}
        </span>
      );
    case "duplicate":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
          <AlertCircle className="h-3 w-3" />
          {t("duplicate")}
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/50 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
          <Clock className="h-3 w-3 animate-pulse" />
          {t("pending")}
        </span>
      );
  }
}

/**
 * Component listing escalation requests submitted by the logged-in user.
 *
 * @returns Component JSX element.
 */
export function MyEscalations() {
  const { data: requests, isLoading } = useMyEscalations();
  const t = useTranslations("HelpRequests");

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Help Requests</CardTitle>
          <CardDescription>Metadata correction requests submitted to custodians</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2].map(i => (
            <div key={i} className="h-16 rounded bg-muted animate-pulse" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!requests || requests.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">{t("helpRequestsTitle")}</CardTitle>
          <CardDescription>{t("helpRequestsDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground text-center">
            <HelpCircle className="h-8 w-8 mb-2 opacity-40" />
            <p className="text-sm font-medium">{t("noHelpRequestsSubmitted")}</p>
            <p className="text-xs mt-1">{t("helpRequestsHint")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">
          {t("helpRequestsTitle")} ({requests.length})
        </CardTitle>
        <CardDescription>{t("trackStatusDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {requests.map(esc => {
          const href = getTargetHref(esc);
          const isDeletion = esc.request_type === "deletion" || !esc.field_name;
          return (
            <div
              key={esc.id}
              className={`rounded-lg border p-4 text-xs shadow-xs space-y-3 ${
                isDeletion ? "border-destructive/30 bg-destructive/5 dark:bg-destructive/10" : "border-border bg-card"
              }`}
              data-testid="my-escalation-card"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <RequestTypeBadge type={esc.request_type} />
                    <StatusBadge status={esc.status} />
                    {href ? (
                      <Link
                        href={href}
                        className="font-medium text-foreground hover:underline inline-flex items-center gap-1"
                      >
                        <span>{getTargetLabel(esc)}</span>
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </Link>
                    ) : (
                      <span className="font-medium text-foreground">{getTargetLabel(esc)}</span>
                    )}
                  </div>
                  {isDeletion ? (
                    <div className="text-xs text-foreground bg-background/80 p-2.5 rounded border border-border/40 mt-1">
                      <span className="font-semibold text-muted-foreground block mb-0.5">
                        {t("reasonForDeletion")}:
                      </span>
                      {esc.note || "—"}
                    </div>
                  ) : (
                    <div className="flex items-baseline gap-2 text-xs">
                      <span className="font-mono font-medium text-muted-foreground uppercase text-[10px]">
                        {esc.field_name}
                      </span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-mono text-foreground">{esc.suggested_value}</span>
                    </div>
                  )}
                </div>
                {esc.created_at && (
                  <span className="text-[10px] text-muted-foreground tabular-nums shrink-0">
                    {formatDate(esc.created_at)}
                  </span>
                )}
              </div>

              {esc.resolution_note && (
                <div className="rounded bg-muted/60 p-2 text-[11px] italic text-muted-foreground border-l-2 border-primary/50">
                  {t("custodianNote")}: &ldquo;{esc.resolution_note}&rdquo;
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
