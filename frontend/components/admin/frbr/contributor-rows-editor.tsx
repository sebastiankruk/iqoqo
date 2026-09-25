// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import type { FrbrContribution } from "@/lib/api/admin";
import { normalizeContributorName } from "../frbr-editor";

/**
 * Props for the ContributorRowsEditor component.
 */
interface ContributorRowsEditorProps {
  /** Available roles for this FRBR level. */
  roles: string[];
  /** Current contribution rows. */
  contributions: FrbrContribution[];
  /** Callback when contributions change. */
  onChange: (contributions: FrbrContribution[]) => void;
}

/**
 * Structured contributor row editor.
 *
 * Renders a list of contributor rows (Role dropdown + Agent Name input)
 * with add/remove controls.  Agent names are normalized on blur.
 *
 * @param props - Component properties
 * @param props.roles - Available roles for this FRBR level
 * @param props.contributions - Current contribution rows
 * @param props.onChange - Callback when contributions change
 * @returns Contributor rows editor JSX element
 */
export function ContributorRowsEditor({ roles, contributions, onChange }: ContributorRowsEditorProps) {
  const [internalIdCounter, setInternalIdCounter] = useState(0);
  const [rows, setRows] = useState<(FrbrContribution & { _internalId: number })[]>(() =>
    contributions.map((c, i) => ({ ...c, _internalId: i }))
  );
  const nameInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    setRows(contributions.map((c, i) => ({ ...c, _internalId: i })));
    setInternalIdCounter(contributions.length);
  }, [contributions]);

  const updateRows = (next: (FrbrContribution & { _internalId: number })[]) => {
    setRows(next);
    onChange(next.map(({ _internalId, ...rest }) => rest));
  };

  const handleAdd = () => {
    const defaultRole = roles[0] ?? "contributor";
    const newId = internalIdCounter;
    setInternalIdCounter(prev => prev + 1);
    const newRow = { role: defaultRole, name: "", sequence: rows.length, _internalId: newId };
    const next = [...rows, newRow];
    updateRows(next);
    setTimeout(() => {
      const idx = next.findIndex(r => r._internalId === newId);
      nameInputRefs.current[idx]?.focus();
    }, 0);
  };

  const handleRemove = (index: number) => {
    const next = rows.filter((_, i) => i !== index).map((r, i) => ({ ...r, sequence: i }));
    updateRows(next);
  };

  const handleRoleChange = (index: number, role: string) => {
    const next = rows.map((r, i) => (i === index ? { ...r, role } : r));
    updateRows(next);
  };

  const handleNameChange = (index: number, name: string) => {
    const next = rows.map((r, i) => (i === index ? { ...r, name } : r));
    updateRows(next);
  };

  const handleNameBlur = (index: number) => {
    const row = rows[index];
    if (!row) return;
    const normalized = normalizeContributorName(row.name);
    if (normalized !== row.name) {
      const next = rows.map((r, i) => (i === index ? { ...r, name: normalized } : r));
      updateRows(next);
    }
    const duplicate = rows.some(
      (r, i) => i !== index && r.name.toLowerCase() === normalized.toLowerCase() && r.role === row.role
    );
    if (duplicate && normalized) {
      console.warn(`Duplicate contributor: ${normalized} (${row.role})`);
    }
  };

  const formatRole = (role: string) => role.charAt(0).toUpperCase() + role.slice(1);

  return (
    <div className="space-y-2 border-t pt-4 mt-4" data-testid="contributor-rows-editor">
      <h4 className="text-sm font-semibold">Contributors</h4>

      {rows.length === 0 && (
        <p className="text-sm text-muted-foreground italic">No contributors yet. Click "Add Contributor" to begin.</p>
      )}

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {rows.map((row, idx) => (
          <div key={row._internalId} className="flex gap-2 items-center" data-testid={`contributor-row-${idx}`}>
            <select
              value={row.role}
              onChange={e => handleRoleChange(idx, e.target.value)}
              className="flex h-9 rounded-md border border-input bg-background px-2 py-1 text-sm"
              data-testid={`contributor-role-${idx}`}
              aria-label={`Role for contributor ${idx + 1}`}
            >
              {roles.map(r => (
                <option key={r} value={r}>
                  {formatRole(r)}
                </option>
              ))}
            </select>
            <input
              ref={el => {
                nameInputRefs.current[idx] = el;
              }}
              value={row.name}
              onChange={e => handleNameChange(idx, e.target.value)}
              onBlur={() => handleNameBlur(idx)}
              placeholder="Contributor name"
              className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 py-1 text-sm"
              data-testid={`contributor-name-${idx}`}
              aria-label={`Name for contributor ${idx + 1}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleRemove(idx)}
              data-testid={`contributor-remove-${idx}`}
              aria-label={`Remove contributor ${row.name || `row ${idx + 1}`}`}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ))}
      </div>

      <Button type="button" variant="outline" size="sm" onClick={handleAdd} data-testid="contributor-add">
        <Plus className="h-4 w-4 mr-1" />
        Add Contributor
      </Button>
    </div>
  );
}
