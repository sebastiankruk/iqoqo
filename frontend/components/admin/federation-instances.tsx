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
import { toast } from "sonner";
import {
  Building2,
  CheckCircle2,
  Globe,
  Loader2,
  Plus,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  XCircle,
} from "lucide-react";
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

function getTrustBadge(trust: TrustLevel) {
  switch (trust) {
    case "trusted":
      return (
        <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-1">
          <ShieldCheck className="h-3 w-3" /> Trusted
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="outline" className="text-yellow-600 border-yellow-500/40 flex items-center gap-1">
          <Shield className="h-3 w-3" /> Pending Review
        </Badge>
      );
    case "blocked":
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <ShieldAlert className="h-3 w-3" /> Blocked
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary" className="text-muted-foreground flex items-center gap-1">
          <XCircle className="h-3 w-3" /> Untrusted
        </Badge>
      );
  }
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  try {
    const date = new Date(dateStr);
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 60) return "Just now";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  } catch {
    return dateStr;
  }
}

export function FederationInstancesManager() {
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
      toast.success(`Discovered and registered instance ${domain}`);
      setNewDomain("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add instance");
    }
  };

  const handleTrustChange = async (instance: FederationInstance, newTrust: TrustLevel) => {
    try {
      await updateTrust.mutateAsync({ instanceId: instance.id, trustLevel: newTrust });
      toast.success(`Updated trust level for ${instance.domain} to ${newTrust}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update trust");
    }
  };

  const confirmDelete = async () => {
    if (!instanceToDelete) return;
    try {
      await removeInstance.mutateAsync(instanceToDelete.id);
      toast.success(`Removed instance ${instanceToDelete.domain}`);
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
            Discover & Connect Peer Instance
          </CardTitle>
          <CardDescription>
            Probe a remote ActivityPub Fediverse instance using NodeInfo to establish federation and sync metadata.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAddInstance} className="flex flex-col sm:flex-row gap-3 items-center">
            <div className="relative w-full max-w-md">
              <Globe className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="library.example.org"
                value={newDomain}
                onChange={e => setNewDomain(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <Button type="submit" disabled={!newDomain.trim() || addInstance.isPending}>
              {addInstance.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Probing...
                </>
              ) : (
                <>
                  <Building2 className="h-4 w-4 mr-2" />
                  Add Peer
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
              Connected Fediverse Instances ({instances.length})
            </span>
          </CardTitle>
          <CardDescription>
            Configure trust policies for connected instances. Metadata from trusted peers is automatically reconciled.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="p-8 flex items-center justify-center text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Loading registered instances...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-md bg-destructive/10 text-destructive text-sm">
              Failed to load instances: {error instanceof Error ? error.message : "Unknown error"}
            </div>
          ) : instances.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground space-y-2">
              <Globe className="h-8 w-8 mx-auto opacity-40" />
              <p className="text-sm font-medium">No peer instances registered yet</p>
              <p className="text-xs">Add a remote library instance above to begin sharing metadata.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/40 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">Domain</th>
                    <th className="px-4 py-3 font-medium">Software</th>
                    <th className="px-4 py-3 font-medium">Trust Level</th>
                    <th className="px-4 py-3 font-medium">Last Probed</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {instances.map(inst => (
                    <tr key={inst.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium flex items-center gap-2">
                        <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span>{inst.domain}</span>
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
                          {getTrustBadge(inst.trust_level)}
                          <select
                            value={inst.trust_level}
                            onChange={e => handleTrustChange(inst, e.target.value as TrustLevel)}
                            disabled={updateTrust.isPending}
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
                        {formatRelativeTime(inst.last_seen_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setInstanceToDelete(inst)}
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                          title="Remove Instance"
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
            <AlertDialogTitle>Remove Peer Instance</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove <span className="font-semibold">{instanceToDelete?.domain}</span>? This
              will terminate metadata sync with this instance.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Remove Peer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
