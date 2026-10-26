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
import { Building2, Copy, Globe, Loader2, Plus, Shield, ShieldAlert, ShieldCheck, Trash2, XCircle } from "lucide-react";
import {
  useFederationInstances,
  useAddFederationInstance,
  useUpdateInstanceTrust,
  useRemoveFederationInstance,
} from "@/lib/api/hooks/federation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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

const TRUST_LEVELS: TrustLevel[] = ["untrusted", "pending", "trusted", "blocked"];

/**
 * Render trust level badge component with associated icon and style.
 *
 * @param trust - Instance trust level ('untrusted' | 'pending' | 'trusted' | 'blocked').
 * @param t - Translator function for AdminFederation namespace.
 * @returns Badge element.
 */
function getTrustBadge(trust: TrustLevel, t: ReturnType<typeof useTranslations>) {
  switch (trust) {
    case "trusted":
      return (
        <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-1">
          <ShieldCheck className="h-3 w-3" /> {t("trustTrusted")}
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="outline" className="text-yellow-600 border-yellow-500/40 flex items-center gap-1">
          <Shield className="h-3 w-3" /> {t("trustPending")}
        </Badge>
      );
    case "blocked":
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <ShieldAlert className="h-3 w-3" /> {t("trustBlocked")}
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary" className="text-muted-foreground flex items-center gap-1">
          <XCircle className="h-3 w-3" /> {t("trustUntrusted")}
        </Badge>
      );
  }
}

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
                          {getTrustBadge(inst.trust_level, t)}
                          <select
                            value={inst.trust_level}
                            onChange={e => handleTrustChange(inst, e.target.value as TrustLevel)}
                            disabled={updateTrust.isPending}
                            aria-label={`Change trust level for ${inst.domain}`}
                            className="text-xs h-7 rounded border border-input bg-background px-2 py-0.5 shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                          >
                            {TRUST_LEVELS.map(lvl => (
                              <option key={lvl} value={lvl}>
                                {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
                              </option>
                            ))}
                          </select>
                        </div>
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
