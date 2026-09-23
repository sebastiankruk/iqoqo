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
import { Button } from "@/components/ui/button";
import { Plus, X, Loader2 } from "lucide-react";
import { useUserSearch } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";

/**
 * A contributor record from the API.
 */
export interface Contributor {
  id: number;
  entity_type: string;
  entity_id: number;
  contributor_name: string;
  contributor_id?: string;
  role: string;
}

/**
 * Props for the ContributorEditor component.
 */
interface ContributorEditorProps {
  entityType: "work" | "expression" | "manifestation";
  entityId: number;
  contributors?: Contributor[];
  onChanged?: () => void;
}

/**
 * Role options based on entity type.
 */
const ROLES_BY_TYPE: Record<string, string[]> = {
  work: ["author", "editor", "translator", "illustrator"],
  expression: ["performer", "director", "conductor", "narrator"],
  manifestation: ["publisher", "printer", "distributor"],
};

/**
 * Role-aware contributor lookup and attribution management.
 * Supports Works (creators), Expressions (realizers/performers),
 * and Manifestations (publishers).
 *
 * @param props - Component properties
 * @param props.entityType - The FRBR entity type
 * @param props.entityId - The entity ID
 * @param props.contributors - Existing contributors
 * @param props.onChanged - Optional callback when contributors change
 * @returns JSX element
 */
export function ContributorEditor({ entityType, entityId, contributors = [], onChanged }: ContributorEditorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRole, setSelectedRole] = useState(ROLES_BY_TYPE[entityType]?.[0] ?? "author");
  const [adding, setAdding] = useState(false);
  const { data: searchResults = [], isLoading: searching } = useUserSearch(searchQuery, searchQuery.length >= 2);

  const roles = ROLES_BY_TYPE[entityType] ?? ["contributor"];

  /**
   * Handles adding a contributor.
   *
   * @param name - The contributor name
   * @param contributorId - Optional user ID
   */
  const handleAdd = async (name: string, contributorId?: string) => {
    setAdding(true);
    try {
      await apiClient.post(`/v1/admin/frbr/contributions`, {
        entity_type: entityType,
        entity_id: entityId,
        contributor_name: name,
        contributor_id: contributorId,
        role: selectedRole,
      });
      toast.success(`Added ${name} as ${selectedRole}`);
      setSearchQuery("");
      onChanged?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add contributor");
    } finally {
      setAdding(false);
    }
  };

  /**
   * Handles removing a contributor.
   *
   * @param contributionId - The contribution ID to remove
   */
  const handleRemove = async (contributionId: number) => {
    try {
      await apiClient.delete(`/v1/admin/frbr/contributions/${contributionId}`);
      toast.success("Contributor removed");
      onChanged?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove contributor");
    }
  };

  return (
    <div className="space-y-3 border-t pt-4 mt-4" data-testid="contributor-editor">
      <h4 className="text-sm font-semibold">Contributors</h4>

      {contributors.length > 0 && (
        <div className="space-y-1">
          {contributors.map(c => (
            <div key={c.id} className="flex items-center justify-between text-sm">
              <span>
                {c.contributor_name} <span className="text-muted-foreground">({c.role})</span>
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => handleRemove(c.id)}
              >
                <X className="w-3 h-3 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <input
            placeholder="Search contributors..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
          />
          {searching && (
            <Loader2 className="absolute right-2 top-2 animate-spin h-4 w-4 text-muted-foreground" />
          )}
          {searchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 border rounded-md bg-popover shadow-md max-h-40 overflow-auto">
              {searchResults.map(user => (
                <button
                  key={user.id}
                  type="button"
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-accent"
                  disabled={adding}
                  onClick={() => handleAdd(user.display_name || user.email, user.id)}
                >
                  {user.display_name || user.email}
                </button>
              ))}
            </div>
          )}
        </div>
        <select
          value={selectedRole}
          onChange={e => setSelectedRole(e.target.value)}
          className="flex h-8 rounded-md border border-input bg-background px-2 py-1 text-sm"
        >
          {roles.map(r => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={adding || !searchQuery.trim()}
          onClick={() => handleAdd(searchQuery.trim())}
        >
          {adding ? <Loader2 className="animate-spin h-4 w-4" /> : <Plus className="h-4 w-4 mr-1" />}
          Add
        </Button>
      </div>
    </div>
  );
}
