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
import { Plus, Users, ChevronDown, ChevronUp } from "lucide-react";
import { getRoles } from "@/lib/api/admin";

interface GroupManagementProps {
  /** Callback when create group is clicked */
  onCreateGroup: () => void;
}

interface RoleData {
  id: number;
  name: string;
  memberCount?: number;
  description?: string;
  color?: string;
}

/**
 * Group/Roles management component.
 *
 * @param props - Component props
 * @param props.onCreateGroup - Callback when create group is clicked
 * @returns The group management component
 */
export function GroupManagement({ onCreateGroup }: GroupManagementProps) {
  const [expandedGroup, setExpandedGroup] = useState<number | null>(null);
  const [roles, setRoles] = useState<RoleData[]>([]);
  const [loading, setLoading] = useState(true);

  // Load roles on mount
  useEffect(() => {
    getRoles()
      .then(roleData => {
        const mappedRoles: RoleData[] = roleData.map((r, idx) => ({
          id: r.id,
          name: r.name,
          memberCount: 0,
          description: `${r.name.charAt(0).toUpperCase() + r.name.slice(1)} role`,
          color: ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"][idx % 5],
        }));
        setRoles(mappedRoles);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-xl font-bold text-foreground">Group Management</h2>
          <p className="mt-1 text-sm text-muted-foreground">Configure groups and their associated privileges</p>
        </div>
        <button
          onClick={onCreateGroup}
          className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          Create Group
        </button>
      </div>

      {/* Group Cards */}
      <div className="space-y-4">
        {roles.map(group => {
          const isExpanded = expandedGroup === group.id;

          return (
            <div key={group.id} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {/* Group Header */}
              <button
                onClick={() => setExpandedGroup(isExpanded ? null : group.id)}
                className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-muted/30"
              >
                <div className="flex items-center gap-4">
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-xl"
                    style={{ backgroundColor: `${group.color}15` }}
                  >
                    <Users className="h-6 w-6" style={{ color: group.color }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">{group.name}</h3>
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: group.color }} />
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground">{group.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">{group.memberCount || 0} members</p>
                    <p className="text-xs text-muted-foreground">Privileges managed via User Access</p>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </button>

              {/* Expanded Privileges */}
              {isExpanded && (
                <div className="border-t border-border bg-muted/10 p-4">
                  <p className="text-sm text-muted-foreground">
                    Role-based privileges are managed through the role assignment in User Access Control.
                  </p>

                  {/* Save Changes Button */}
                  <div className="mt-6 flex justify-end">
                    <button className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-opacity hover:opacity-90">
                      Save Changes
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
