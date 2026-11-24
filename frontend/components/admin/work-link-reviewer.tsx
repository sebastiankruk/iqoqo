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
import { useTranslations } from "next-intl";
import { ArrowRight, Check, GitBranch, Plus, Search, Sparkles, Trash2, X } from "lucide-react";
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  acceptWorkLinkCandidate,
  createWorkRelation,
  deleteWorkRelation,
  dismissWorkLinkCandidate,
  listWorkLinkCandidates,
  listWorkRelations,
  scanWorkLinks,
  type WorkLinkCandidate,
  type WorkLinkScanReport,
  type WorkRelationItem,
  type WorkRelationType,
} from "@/lib/api/admin";
import { apiClient } from "@/lib/api/client";

const RELATION_TYPES: WorkRelationType[] = [
  "is_adaptation_of",
  "is_derivative_of",
  "inspired_by",
  "sequel_to",
  "spin_off_of",
  "companion_to",
];

interface WorkSearchResult {
  id: number;
  title: string;
}

interface WorkLinkReviewerProps {
  canEdit: boolean;
}

/**
 * Custodian review queue and manual linker for cross-media FRBR Work relationships.
 */
export function WorkLinkReviewer({ canEdit }: WorkLinkReviewerProps) {
  const t = useTranslations("workLinks");
  const [candidates, setCandidates] = useState<WorkLinkCandidate[]>([]);
  const [relations, setRelations] = useState<WorkRelationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [engine, setEngine] = useState<"heuristic" | "llama">("heuristic");
  const [scanReport, setScanReport] = useState<WorkLinkScanReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"pending" | "confirmed">("pending");
  const [relationChoices, setRelationChoices] = useState<Record<number, WorkRelationType>>({});
  const [unlinkTarget, setUnlinkTarget] = useState<WorkRelationItem | null>(null);

  const [manualOpen, setManualOpen] = useState(false);
  const [sourceQuery, setSourceQuery] = useState("");
  const [targetQuery, setTargetQuery] = useState("");
  const [sourceResults, setSourceResults] = useState<WorkSearchResult[]>([]);
  const [targetResults, setTargetResults] = useState<WorkSearchResult[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [manualRelationType, setManualRelationType] = useState<WorkRelationType>("is_adaptation_of");

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [candRes, relRes] = await Promise.all([
        listWorkLinkCandidates({ status: "pending", limit: 50 }),
        listWorkRelations({ limit: 50 }),
      ]);
      setCandidates(candRes.items);
      setRelations(relRes.items);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load work links");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listWorkLinkCandidates({ status: "pending", limit: 50 }), listWorkRelations({ limit: 50 })])
      .then(([candRes, relRes]) => {
        if (cancelled) return;
        setCandidates(candRes.items);
        setRelations(relRes.items);
      })
      .catch(err => {
        if (cancelled) return;
        setErrorMsg(err instanceof Error ? err.message : "Failed to load work links");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setErrorMsg(null);
    try {
      const report = await scanWorkLinks({ engine, dry_run: false });
      setScanReport(report);
      await loadData();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to run scan");
    } finally {
      setScanning(false);
    }
  };

  const handleAccept = async (candidate: WorkLinkCandidate) => {
    setErrorMsg(null);
    try {
      const chosenType = relationChoices[candidate.id] ?? candidate.proposed_relation_type;
      await acceptWorkLinkCandidate(candidate.id, { relation_type: chosenType });
      await loadData();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to confirm link");
    }
  };

  const handleDismiss = async (candidateId: number) => {
    setErrorMsg(null);
    try {
      await dismissWorkLinkCandidate(candidateId);
      await loadData();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to dismiss candidate");
    }
  };

  const handleConfirmUnlink = async () => {
    if (!unlinkTarget) return;
    setErrorMsg(null);
    try {
      await deleteWorkRelation(unlinkTarget.id);
      setUnlinkTarget(null);
      await loadData();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to remove link");
    }
  };

  const searchWorks = async (query: string, setter: (rows: WorkSearchResult[]) => void) => {
    const trimmed = query.trim();
    if (!trimmed) {
      setter([]);
      return;
    }
    try {
      const res = await apiClient.get<{ results?: Array<{ entity_id?: number; label?: string }> }>(
        "/v1/catalog/graph/search",
        { params: { q: trimmed, types: "work", limit: 8 } }
      );
      const rows = (res.data?.results ?? [])
        .filter(r => typeof r.entity_id === "number" && typeof r.label === "string")
        .map(r => ({ id: r.entity_id as number, title: r.label as string }));
      setter(rows);
    } catch {
      setter([]);
    }
  };

  const handleCreateManualLink = async () => {
    if (!selectedSourceId || !selectedTargetId) return;
    setErrorMsg(null);
    try {
      await createWorkRelation({
        source_work_id: selectedSourceId,
        target_work_id: selectedTargetId,
        relation_type: manualRelationType,
      });
      setManualOpen(false);
      setSelectedSourceId(null);
      setSelectedTargetId(null);
      setSourceQuery("");
      setTargetQuery("");
      await loadData();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create work relation");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant={activeTab === "pending" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("pending")}
          >
            {t("pendingTab")} ({candidates.length})
          </Button>
          <Button
            type="button"
            variant={activeTab === "confirmed" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("confirmed")}
          >
            {t("confirmedTab")} ({relations.length})
          </Button>
        </div>

        {canEdit && (
          <div className="flex flex-wrap items-center gap-2">
            <Select value={engine} onValueChange={v => setEngine(v as "heuristic" | "llama")}>
              <SelectTrigger className="w-52" aria-label={t("engineLabel")}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="heuristic">{t("engineHeuristic")}</SelectItem>
                <SelectItem value="llama">{t("engineLlama")}</SelectItem>
              </SelectContent>
            </Select>
            <Button type="button" onClick={handleScan} disabled={scanning}>
              <Search className="h-4 w-4 mr-2" />
              {scanning ? t("scanning") : t("scanButton")}
            </Button>
            <Button type="button" variant="outline" onClick={() => setManualOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t("manualLinkButton")}
            </Button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {errorMsg}
        </div>
      )}

      {scanReport && (
        <div className="rounded-md border border-border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
          Scanned {scanReport.works_scanned} works ({scanReport.engine}): {scanReport.candidate_pairs} candidate pairs,{" "}
          {scanReport.created} new candidates queued.
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">Loading...</div>
      ) : activeTab === "pending" ? (
        candidates.length === 0 ? (
          <EmptyState icon={GitBranch} title={t("emptyPending")} description={t("subtitle")} />
        ) : (
          <div className="grid gap-4">
            {candidates.map(cand => (
              <Card key={cand.id}>
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle className="text-base">
                        {cand.source_work_title ?? `Work #${cand.source_work_id}`}
                      </CardTitle>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      <CardTitle className="text-base">
                        {cand.target_work_title ?? `Work #${cand.target_work_id}`}
                      </CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{Math.round(cand.confidence * 100)}%</Badge>
                      <Badge variant={cand.resolution_source === "llm" ? "default" : "secondary"}>
                        {cand.resolution_source === "llm" ? (
                          <span className="flex items-center gap-1">
                            <Sparkles className="h-3 w-3" />
                            {t("provenanceLlama")}
                          </span>
                        ) : (
                          t("provenanceHeuristic")
                        )}
                      </Badge>
                    </div>
                  </div>
                  <CardDescription className="flex flex-wrap gap-2 pt-1">
                    {cand.source_categories.map(cat => (
                      <Badge key={`src-${cand.id}-${cat}`} variant="outline">
                        {cat}
                      </Badge>
                    ))}
                    <span>→</span>
                    {cand.target_categories.map(cat => (
                      <Badge key={`tgt-${cand.id}-${cat}`} variant="outline">
                        {cat}
                      </Badge>
                    ))}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex flex-col gap-2">
                    <Select
                      value={relationChoices[cand.id] ?? cand.proposed_relation_type}
                      onValueChange={v => setRelationChoices(prev => ({ ...prev, [cand.id]: v as WorkRelationType }))}
                    >
                      <SelectTrigger className="w-52">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RELATION_TYPES.map(rt => (
                          <SelectItem key={rt} value={rt}>
                            {rt.replaceAll("_", " ")}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {cand.llm_reasoning && <p className="text-xs text-muted-foreground">{cand.llm_reasoning}</p>}
                  </div>

                  {canEdit && (
                    <div className="flex items-center gap-2">
                      <Button type="button" size="sm" onClick={() => void handleAccept(cand)}>
                        <Check className="h-4 w-4 mr-1" />
                        {t("accept")}
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => void handleDismiss(cand.id)}>
                        <X className="h-4 w-4 mr-1" />
                        {t("dismiss")}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )
      ) : relations.length === 0 ? (
        <EmptyState icon={GitBranch} title={t("emptyConfirmed")} description={t("subtitle")} />
      ) : (
        <div className="grid gap-4">
          {relations.map(rel => (
            <Card key={rel.id}>
              <CardContent className="pt-6 flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2 font-medium">
                    <span>{rel.source_work_title ?? `Work #${rel.source_work_id}`}</span>
                    <Badge variant="secondary">{rel.relation_type.replaceAll("_", " ")}</Badge>
                    <span>{rel.target_work_title ?? `Work #${rel.target_work_id}`}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 text-xs text-muted-foreground">
                    {rel.source_categories.join(", ")} → {rel.target_categories.join(", ")}
                  </div>
                </div>
                {canEdit && (
                  <Button type="button" size="sm" variant="outline" onClick={() => setUnlinkTarget(rel)}>
                    <Trash2 className="h-4 w-4 mr-1" />
                    {t("unlink")}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={unlinkTarget !== null} onOpenChange={open => !open && setUnlinkTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("unlinkConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("unlinkConfirmBody")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("dismiss")}</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleConfirmUnlink()}>{t("unlink")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={manualOpen} onOpenChange={setManualOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("manualTitle")}</DialogTitle>
            <DialogDescription>{t("subtitle")}</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <div>
              <input
                type="text"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={sourceQuery}
                onChange={e => {
                  setSourceQuery(e.target.value);
                  void searchWorks(e.target.value, setSourceResults);
                }}
                placeholder={t("sourceWorkPlaceholder")}
              />
              {sourceResults.length > 0 && (
                <div className="mt-1 border rounded-md max-h-32 overflow-y-auto">
                  {sourceResults.map(w => (
                    <button
                      key={`src-opt-${w.id}`}
                      type="button"
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-muted"
                      onClick={() => {
                        setSelectedSourceId(w.id);
                        setSourceQuery(w.title);
                        setSourceResults([]);
                      }}
                    >
                      {w.title} (#{w.id})
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">{t("relationTypeLabel")}</label>
              <Select value={manualRelationType} onValueChange={v => setManualRelationType(v as WorkRelationType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RELATION_TYPES.map(rt => (
                    <SelectItem key={`manual-${rt}`} value={rt}>
                      {rt.replaceAll("_", " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <input
                type="text"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={targetQuery}
                onChange={e => {
                  setTargetQuery(e.target.value);
                  void searchWorks(e.target.value, setTargetResults);
                }}
                placeholder={t("targetWorkPlaceholder")}
              />
              {targetResults.length > 0 && (
                <div className="mt-1 border rounded-md max-h-32 overflow-y-auto">
                  {targetResults.map(w => (
                    <button
                      key={`tgt-opt-${w.id}`}
                      type="button"
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-muted"
                      onClick={() => {
                        setSelectedTargetId(w.id);
                        setTargetQuery(w.title);
                        setTargetResults([]);
                      }}
                    >
                      {w.title} (#{w.id})
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              onClick={() => void handleCreateManualLink()}
              disabled={!selectedSourceId || !selectedTargetId}
            >
              {t("createLink")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
