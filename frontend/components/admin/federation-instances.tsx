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
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowLeftRight,
  ArrowRight,
  Ban,
  Building2,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Globe,
  Info,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  useFederationInstances,
  useAddFederationInstance,
  useUpdateInstanceTrust,
  useRemoveFederationInstance,
} from "@/lib/api/hooks/federation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import type { FederationInstance, TrustLevel } from "@/types/federation";

const TRUST_LEVELS: TrustLevel[] = ["trusted", "untrusted", "blocked"];

/**
 * Format ISO date string into human-readable relative time.
 *
 * @param dateStr - ISO date string or null.
 * @param t - Translator function for AdminFederation namespace.
 * @returns Formatted relative time string.
 */
function formatRelativeTime(dateStr: string | null, t: ReturnType<typeof useTranslations>): string {
  if (!dateStr) return t("never");
  try {
    const date = new Date(dateStr);
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 60) return t("justNow");
    if (diffSec < 3600) return t("timeMinutesAgo", { m: Math.floor(diffSec / 60) });
    if (diffSec < 86400) return t("timeHoursAgo", { h: Math.floor(diffSec / 3600) });
    return t("timeDaysAgo", { d: Math.floor(diffSec / 86400) });
  } catch {
    return dateStr;
  }
}

/**
 * FederationInstancesManager component for discovering, adding, modifying trust,
 * and removing peer instances.
 *
 * @returns Instance manager component.
 */
export function FederationInstancesManager() {
  const t = useTranslations("AdminFederation");
  const { data: instances = [], isLoading, error } = useFederationInstances();
  const addInstance = useAddFederationInstance();
  const updateTrust = useUpdateInstanceTrust();
  const removeInstance = useRemoveFederationInstance();

  const [newDomain, setNewDomain] = useState("");
  const [instanceToDelete, setInstanceToDelete] = useState<FederationInstance | null>(null);
  const [expandedCapabilitiesId, setExpandedCapabilitiesId] = useState<number | null>(null);

  const handleAddInstance = async (e: React.FormEvent) => {
    e.preventDefault();
    const domain = newDomain.trim();
    if (!domain) return;

    try {
      await addInstance.mutateAsync(domain);
      toast.success(t("discoveredSuccess", { domain }));
      setNewDomain("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add instance");
    }
  };

  const handleTrustChange = async (instance: FederationInstance, newTrust: TrustLevel) => {
    try {
      await updateTrust.mutateAsync({ instanceId: instance.id, trustLevel: newTrust });
      toast.success(t("trustUpdatedSuccess", { domain: instance.domain, trust: newTrust }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update trust");
    }
  };

  const confirmDelete = async () => {
    if (!instanceToDelete) return;
    try {
      await removeInstance.mutateAsync(instanceToDelete.id);
      toast.success(t("instanceRemovedSuccess", { domain: instanceToDelete.domain }));
      setInstanceToDelete(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove instance");
    }
  };

  return (
    <div className="space-y-6">
      {/* Reciprocal Peering Notice Banner */}
      <div
        data-testid="peering-guidance-banner"
        className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/10 text-foreground flex items-start gap-3"
      >
        <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
        <div className="space-y-1 text-xs">
          <p className="font-semibold text-sm text-blue-900 dark:text-blue-200">{t("peeringNoticeTitle")}</p>
          <p className="text-muted-foreground leading-relaxed">{t("peeringNoticeDesc")}</p>
        </div>
      </div>

      {/* Discovery & Add form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Plus className="h-4 w-4 text-primary" />
            {t("discoverTitle")}
          </CardTitle>
          <CardDescription>{t("discoverDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAddInstance} className="flex flex-col sm:flex-row gap-3 items-center">
            <div className="relative w-full max-w-md">
              <Globe className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder={t("domainPlaceholder")}
                value={newDomain}
                onChange={e => setNewDomain(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <Button type="submit" disabled={!newDomain.trim() || addInstance.isPending}>
              {addInstance.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t("probing")}
                </>
              ) : (
                <>
                  <Building2 className="h-4 w-4 mr-2" />
                  {t("addPeer")}
                </>
              )}
            </Button>
          </form>
          <p className="text-xs text-muted-foreground mt-3">{t("addPeerReciprocalNote")}</p>
        </CardContent>
      </Card>

      {/* Instances Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              {t("connectedTitle")} ({instances.length})
            </span>
          </CardTitle>
          <CardDescription>{t("connectedDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="p-8 flex items-center justify-center text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{t("loadingInstances")}</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-md bg-destructive/10 text-destructive text-sm">
              {t("failedLoadInstances")}: {error instanceof Error ? error.message : "Unknown error"}
            </div>
          ) : instances.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground space-y-2">
              <Globe className="h-8 w-8 mx-auto opacity-40" />
              <p className="text-sm font-medium">{t("noInstances")}</p>
              <p className="text-xs">{t("noInstancesDesc")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/40 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("thDomain")}</th>
                    <th className="px-4 py-3 font-medium">{t("thSoftware")}</th>
                    <th className="px-4 py-3 font-medium">{t("thTrustLevel")}</th>
                    <th className="px-4 py-3 font-medium">{t("thPeering")}</th>
                    <th className="px-4 py-3 font-medium">{t("thLastProbed")}</th>
                    <th className="px-4 py-3 font-medium text-right">{t("thActions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {instances.map(inst => (
                    <tr key={inst.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-2">
                          <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span>{inst.domain}</span>
                        </div>
                        {inst.key_fingerprint ? (
                          <div className="flex items-center gap-1.5 mt-1 font-normal">
                            <code className="text-[11px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded border border-border select-all break-all">
                              {inst.key_fingerprint}
                            </code>
                            <button
                              type="button"
                              aria-label={`Copy key fingerprint for ${inst.domain}`}
                              onClick={() => {
                                if (inst.key_fingerprint) {
                                  navigator.clipboard?.writeText(inst.key_fingerprint);
                                  toast.success(t("copiedFingerprint"));
                                }
                              }}
                              className="text-muted-foreground hover:text-foreground p-0.5 transition-colors"
                            >
                              <Copy className="h-3 w-3" />
                            </button>
                          </div>
                        ) : (
                          <div className="text-[11px] font-normal text-muted-foreground/60 mt-1">
                            {t("noFingerprint")}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {inst.software_name ? (
                          <span>
                            {inst.software_name} {inst.software_version || ""}
                          </span>
                        ) : (
                          <span className="text-muted-foreground/60">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <select
                            value={inst.trust_level}
                            onChange={e => handleTrustChange(inst, e.target.value as TrustLevel)}
                            disabled={updateTrust.isPending}
                            aria-label={`Change trust level for ${inst.domain}`}
                            className="text-xs h-7 rounded border border-input bg-background px-2 py-0.5 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring font-medium"
                          >
                            {TRUST_LEVELS.map(lvl => (
                              <option key={lvl} value={lvl}>
                                {lvl === "trusted"
                                  ? t("trustTrusted")
                                  : lvl === "blocked"
                                    ? t("trustBlocked")
                                    : t("trustUntrusted")}
                              </option>
                            ))}
                          </select>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {(() => {
                          const direction =
                            inst.peering_direction || (inst.trust_level === "blocked" ? "blocked" : "outbound_only");
                          const caps = inst.effective_capabilities || {
                            auto_metadata_sync: inst.trust_level === "trusted",
                            custodian_merge_queue: inst.trust_level === "untrusted",
                            friend_follows: inst.trust_level === "trusted",
                            cross_instance_loans: inst.trust_level === "trusted" && direction === "reciprocal",
                          };
                          const isExpanded = expandedCapabilitiesId === inst.id;

                          return (
                            <div className="space-y-1">
                              <div>
                                {direction === "reciprocal" ? (
                                  <Badge
                                    variant="outline"
                                    className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 gap-1 font-medium"
                                  >
                                    <ArrowLeftRight className="h-3 w-3 shrink-0" />
                                    <span>{t("directionReciprocal")}</span>
                                  </Badge>
                                ) : direction === "blocked" ? (
                                  <Badge
                                    variant="outline"
                                    className="bg-destructive/10 text-destructive border-destructive/30 gap-1 font-medium"
                                  >
                                    <Ban className="h-3 w-3 shrink-0" />
                                    <span>{t("directionBlocked")}</span>
                                  </Badge>
                                ) : direction === "inbound_only" ? (
                                  <Badge
                                    variant="outline"
                                    className="bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30 gap-1 font-medium"
                                  >
                                    <ArrowLeft className="h-3 w-3 shrink-0" />
                                    <span>{t("directionInboundOnly")}</span>
                                  </Badge>
                                ) : (
                                  <Badge
                                    variant="outline"
                                    className="bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30 gap-1 font-medium"
                                  >
                                    <ArrowRight className="h-3 w-3 shrink-0" />
                                    <span>{t("directionOutboundOnly")}</span>
                                  </Badge>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => setExpandedCapabilitiesId(isExpanded ? null : inst.id)}
                                aria-expanded={isExpanded}
                                aria-label={`${t("viewCapabilities")} for ${inst.domain}`}
                                className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 font-normal underline decoration-dotted transition-colors"
                              >
                                <Info className="h-3 w-3 shrink-0" />
                                <span>{t("viewCapabilities")}</span>
                                {isExpanded ? (
                                  <ChevronUp className="h-3 w-3 shrink-0" />
                                ) : (
                                  <ChevronDown className="h-3 w-3 shrink-0" />
                                )}
                              </button>
                              {isExpanded && (
                                <div
                                  data-testid={`capabilities-matrix-${inst.id}`}
                                  className="mt-2 p-2.5 rounded-lg border border-border bg-muted/40 text-xs space-y-1.5 text-muted-foreground max-w-xs sm:max-w-sm"
                                >
                                  <p className="font-semibold text-foreground text-[11px] uppercase tracking-wide">
                                    {t("capabilitiesTitle")}
                                  </p>
                                  <p className="text-[11px] leading-tight text-foreground/80">
                                    {direction === "reciprocal"
                                      ? t("directionReciprocalDesc")
                                      : direction === "blocked"
                                        ? t("directionBlockedDesc")
                                        : direction === "inbound_only"
                                          ? t("directionInboundOnlyDesc")
                                          : t("directionOutboundOnlyDesc")}
                                  </p>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-1 pt-1.5 border-t border-border/60">
                                    <div className="flex items-center gap-1.5">
                                      {caps.auto_metadata_sync ? (
                                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                      ) : (
                                        <X className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                                      )}
                                      <span>{t("capAutoMetadataSync")}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      {caps.custodian_merge_queue ? (
                                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                      ) : (
                                        <X className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                                      )}
                                      <span>{t("capCustodianMergeQueue")}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      {caps.friend_follows ? (
                                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                      ) : (
                                        <X className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                                      )}
                                      <span>{t("capFriendFollows")}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      {caps.cross_instance_loans ? (
                                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                                      ) : (
                                        <X className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                                      )}
                                      <span>{t("capCrossInstanceLoans")}</span>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">
                        {formatRelativeTime(inst.last_seen_at, t)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setInstanceToDelete(inst)}
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                          title="Remove Instance"
                          aria-label={t("removeInstanceAria", { domain: inst.domain })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <AlertDialog open={Boolean(instanceToDelete)} onOpenChange={open => !open && setInstanceToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("removeTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("removeDesc", { domain: instanceToDelete?.domain ?? "" })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("removePeer")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
