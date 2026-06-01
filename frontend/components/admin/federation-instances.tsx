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

import { useState, useEffect } from "react";
import {
  getFederationInstances,
  addFederationInstance,
  updateInstanceTrust,
  removeFederationInstance,
} from "@/lib/api/federation";
import { Button } from "@/components/ui/button";
import { Loader2, Plus, Trash2, Globe } from "lucide-react";
import type { FederationInstance, TrustLevel } from "@/types/federation";

const TRUST_COLORS: Record<TrustLevel, string> = {
  untrusted: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
  pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  trusted: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  blocked: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

/**
 * Manages federated instance list with trust level controls.
 * @returns {JSX.Element} The component
 */
export function FederationInstances() {
  const [instances, setInstances] = useState<FederationInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [newDomain, setNewDomain] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInstances = async () => {
    try {
      const data = await getFederationInstances();
      setInstances(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load instances");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstances();
  }, []);

  const handleAdd = async () => {
    if (!newDomain.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await addFederationInstance(newDomain.trim());
      setNewDomain("");
      await fetchInstances();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add instance");
    } finally {
      setAdding(false);
    }
  };

  const handleTrustChange = async (instanceId: number, trustLevel: TrustLevel) => {
    try {
      await updateInstanceTrust(instanceId, trustLevel);
      await fetchInstances();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update trust");
    }
  };

  const handleRemove = async (instanceId: number) => {
    try {
      await removeFederationInstance(instanceId);
      await fetchInstances();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove instance");
    }
  };

  if (loading) {
    return <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />;
  }

  return (
    <div className="space-y-6">
      {/* Add Instance */}
      <div className="flex gap-3">
        <input
          type="text"
          className="flex h-9 flex-1 max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={newDomain}
          onChange={e => setNewDomain(e.target.value)}
          placeholder="Enter domain (e.g., books.example.com)"
          onKeyDown={e => e.key === "Enter" && handleAdd()}
        />
        <Button size="sm" onClick={handleAdd} disabled={adding || !newDomain.trim()}>
          {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
          Add
        </Button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Instances Table */}
      {instances.length === 0 ? (
        <p className="text-sm text-muted-foreground">No federation instances configured.</p>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Domain</th>
                <th className="text-left px-4 py-2 font-medium">Software</th>
                <th className="text-left px-4 py-2 font-medium">Trust</th>
                <th className="text-left px-4 py-2 font-medium">Last Seen</th>
                <th className="text-right px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {instances.map(instance => (
                <tr key={instance.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      {instance.domain}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {instance.software_name || "—"}
                    {instance.software_version && ` v${instance.software_version}`}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      className="text-xs px-2 py-1 rounded border border-input bg-transparent"
                      value={instance.trust_level}
                      onChange={e => handleTrustChange(instance.id, e.target.value as TrustLevel)}
                    >
                      <option value="untrusted">Untrusted</option>
                      <option value="pending">Pending</option>
                      <option value="trusted">Trusted</option>
                      <option value="blocked">Blocked</option>
                    </select>
                    <span className={`ml-2 text-xs px-2 py-0.5 rounded ${TRUST_COLORS[instance.trust_level]}`}>
                      {instance.trust_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {instance.last_seen_at ? new Date(instance.last_seen_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" onClick={() => handleRemove(instance.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
