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

import { BookOpen, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { IsbnMeta } from "@/types/frbr";

type ExistingSerialIssue = NonNullable<IsbnMeta["existing_issues"]>[number];

interface SerialDisambiguationModalProps {
  disambiguation: IsbnMeta;
  onSelectIssue: (issue: ExistingSerialIssue) => void;
  onAddNewIssue: () => void;
  onDismiss: () => void;
}

/**
 * Interactive modal shown when a bare 13-digit GS1 977 barcode is scanned
 * without an EAN-2 issue add-on, allowing selection of an existing issue or
 * pre-filled creation of a new issue under the parent Serial Work.
 */
export function SerialDisambiguationModal({
  disambiguation,
  onSelectIssue,
  onAddNewIssue,
  onDismiss,
}: SerialDisambiguationModalProps) {
  const t = useTranslations("scanner");
  const issues = disambiguation.existing_issues ?? [];

  return (
    <div
      data-testid="serial-disambiguation-modal"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
    >
      <div className="w-full max-w-lg rounded-t-2xl sm:rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-serif font-bold text-foreground">{t("serialDisambiguation.title")}</h2>
            <p className="text-xs text-muted-foreground mt-1">{t("serialDisambiguation.description")}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/60 bg-muted/30 p-3 text-sm">
          <span className="font-semibold text-foreground">{disambiguation.title}</span>
          {disambiguation.issn && (
            <Badge variant="outline" className="font-mono text-xs">
              ISSN {disambiguation.issn}
            </Badge>
          )}
          {disambiguation.ean && (
            <Badge variant="secondary" className="font-mono text-xs">
              EAN {disambiguation.ean}
            </Badge>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t("serialDisambiguation.existingIssuesLabel")}
          </div>
          {issues.length > 0 ? (
            <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
              {issues.map(issue => {
                const badgeText =
                  issue.cumulative_issue_number != null
                    ? `${issue.issue_number || "?"}(${issue.cumulative_issue_number})`
                    : issue.issue_number || issue.full_barcode || "#";
                return (
                  <button
                    key={issue.manifestation_id}
                    type="button"
                    onClick={() => onSelectIssue(issue)}
                    data-testid={`serial-issue-option-${issue.manifestation_id}`}
                    className="w-full flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/60 px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/50 hover:bg-muted/40"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <BookOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="font-mono text-xs">
                            {badgeText}
                          </Badge>
                          {issue.publication_year && (
                            <span className="text-xs text-muted-foreground">
                              {issue.publication_month ? `${issue.publication_month}/` : ""}
                              {issue.publication_year}
                            </span>
                          )}
                        </div>
                        {issue.cover_headline && (
                          <p className="truncate text-xs text-muted-foreground mt-0.5">{issue.cover_headline}</p>
                        )}
                      </div>
                    </div>
                    <span className="shrink-0 text-xs font-medium text-primary">
                      {t("serialDisambiguation.selectIssue")}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground py-2">{t("serialDisambiguation.noIssuesYet")}</p>
          )}
        </div>

        <div className="flex justify-end pt-2 border-t border-border">
          <Button type="button" onClick={onAddNewIssue} data-testid="add-new-serial-issue-button" className="gap-1.5">
            <Plus className="h-4 w-4" />
            <span>{t("serialDisambiguation.addNewIssue")}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
