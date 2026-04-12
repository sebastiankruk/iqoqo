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
import { Plus, Users, ChevronDown, ChevronUp, Save, Trash2, X } from "lucide-react";
import {
  getRoles,
  getPermissions,
  getRolePermissions,
  updateRolePermissions,
  createRole,
  deleteRole,
  Permission,
  Role as RoleType,
} from "@/lib/api/admin";

interface RoleData {
  id: number;
  name: string;
  memberCount?: number;
  description: string;
  color: string;
  is_protected: boolean;
}

/**
 * Role management component - allows assigning permissions to roles.
 *
 * @returns The role management component
 */
export function GroupManagement() {
  const [expandedRole, setExpandedRole] = useState<number | null>(null);
  const [roles, setRoles] = useState<RoleData[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [rolePermissions, setRolePermissions] = useState<Record<number, number[]>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);

  // Create role modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [creating, setCreating] = useState(false);

  // Delete role modal state
  const [roleToDelete, setRoleToDelete] = useState<RoleData | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Load roles and permissions on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [roleData, permData] = await Promise.all([getRoles(), getPermissions()]);
      const protectedRoles = ["admin", "user", "contributor"];
      const mappedRoles: RoleData[] = roleData.map((r: RoleType, idx: number) => ({
        id: r.id,
        name: r.name,
        memberCount: 0,
        description: `${r.name.charAt(0).toUpperCase() + r.name.slice(1)} role`,
        color: ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"][idx % 5],
        is_protected: protectedRoles.includes(r.name.toLowerCase()),
      }));
      setRoles(mappedRoles);
      setPermissions(permData);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  };

  // Load role permissions when a role is expanded
  const handleExpand = async (roleId: number) => {
    if (expandedRole === roleId) {
      setExpandedRole(null);
      return;
    }

    setExpandedRole(roleId);

    if (rolePermissions[roleId] === undefined) {
      try {
        const perms = await getRolePermissions(roleId);
        setRolePermissions(prev => ({ ...prev, [roleId]: perms.permission_ids }));
      } catch (err) {
        console.error("Failed to fetch role permissions:", err);
      }
    }
  };

  const togglePermission = (roleId: number, permId: number) => {
    setRolePermissions(prev => {
      const current = prev[roleId] || [];
      if (current.includes(permId)) {
        return { ...prev, [roleId]: current.filter(p => p !== permId) };
      }
      return { ...prev, [roleId]: [...current, permId] };
    });
  };

  const handleSavePermissions = async (roleId: number) => {
    setSaving(roleId);
    try {
      const perms = rolePermissions[roleId] || [];
      await updateRolePermissions(roleId, perms);
    } catch (err) {
      console.error("Failed to save role permissions:", err);
    } finally {
      setSaving(null);
    }
  };

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return;
    setCreating(true);
    try {
      const newRole = await createRole(newRoleName.trim());
      const protectedRoles = ["admin", "user", "contributor"];
      const roleData: RoleData = {
        id: newRole.id,
        name: newRole.name,
        memberCount: 0,
        description: `${newRole.name.charAt(0).toUpperCase() + newRole.name.slice(1)} role`,
        color: ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"][roles.length % 5],
        is_protected: protectedRoles.includes(newRole.name.toLowerCase()),
      };
      setRoles(prev => [...prev, roleData]);
      setShowCreateModal(false);
      setNewRoleName("");
    } catch (err) {
      console.error("Failed to create role:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteRole = async () => {
    if (!roleToDelete) return;
    setDeleting(true);
    try {
      await deleteRole(roleToDelete.id);
      setRoles(prev => prev.filter(r => r.id !== roleToDelete.id));
      setRoleToDelete(null);
    } catch (err) {
      console.error("Failed to delete role:", err);
    } finally {
      setDeleting(false);
    }
  };

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
          <h2 className="font-serif text-xl font-bold text-foreground">Roles</h2>
          <p className="mt-1 text-sm text-muted-foreground">Configure roles and their assigned permissions</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          Add Role
        </button>
      </div>

      {/* Role Cards */}
      <div className="space-y-4">
        {roles.map(role => {
          const isExpanded = expandedRole === role.id;
          const currentPerms = rolePermissions[role.id] || [];

          return (
            <div key={role.id} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {/* Role Header */}
              <button
                onClick={() => handleExpand(role.id)}
                className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-muted/30"
              >
                <div className="flex items-center gap-4">
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-xl"
                    style={{ backgroundColor: `${role.color}15` }}
                  >
                    <Users className="h-6 w-6" style={{ color: role.color }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">{role.name}</h3>
                      {role.is_protected && (
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Protected</span>
                      )}
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: role.color }} />
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground">{role.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">{currentPerms.length} permissions</p>
                    <p className="text-xs text-muted-foreground">{role.memberCount || 0} users</p>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </button>

              {/* Expanded Permissions */}
              {isExpanded && (
                <div className="border-t border-border bg-muted/10 p-4">
                  <p className="text-sm text-muted-foreground mb-4">
                    Assign permissions to control what users with this role can do.
                  </p>

                  {/* Permissions Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {permissions.map(perm => (
                      <label
                        key={perm.id}
                        className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background hover:bg-muted/50 cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={currentPerms.includes(perm.id)}
                          onChange={() => togglePermission(role.id, perm.id)}
                          className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                        />
                        <div>
                          <p className="text-sm font-medium text-foreground">{perm.name}</p>
                          {perm.description && <p className="text-xs text-muted-foreground">{perm.description}</p>}
                        </div>
                      </label>
                    ))}
                  </div>

                  {/* Actions */}
                  <div className="mt-6 flex justify-between">
                    {!role.is_protected && (
                      <button
                        onClick={() => setRoleToDelete(role)}
                        className="flex items-center gap-2 rounded-lg border border-destructive px-4 py-2 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-opacity"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete Role
                      </button>
                    )}
                    <div className="flex justify-end ml-auto">
                      <button
                        onClick={() => handleSavePermissions(role.id)}
                        disabled={saving === role.id}
                        className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                      >
                        {saving === role.id ? (
                          <>
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent-foreground border-t-transparent" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4" />
                            Save Changes
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Create Role Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">Add New Role</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground">Role Name</label>
                <input
                  type="text"
                  value={newRoleName}
                  onChange={e => setNewRoleName(e.target.value)}
                  placeholder="e.g., moderator, editor"
                  className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateRole}
                  disabled={!newRoleName.trim() || creating}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Role"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Role Modal */}
      {roleToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-foreground">Delete Role</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Are you sure you want to delete the role &quot;{roleToDelete.name}&quot;? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setRoleToDelete(null)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteRole}
                disabled={deleting}
                className="rounded-lg bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground hover:opacity-90 disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
