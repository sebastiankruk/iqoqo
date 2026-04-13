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
import { AdminUser, updateUser, getRoles } from "@/lib/api/admin";
import { Loader2, X, ShieldAlert } from "lucide-react";

interface RbacSheetProps {
  /** The user to edit */
  user: AdminUser;
  /** Callback when sheet closes */
  onClose: () => void;
  /** Callback when user is updated */
  onUpdate: (updated: AdminUser) => void;
  /** Whether user has write:users permission */
  canEdit?: boolean;
}

/**
 * Slide-over interface for managing user properties and RBAC assignments.
 *
 * @param props - Component props
 * @param props.user - The user to edit
 * @param props.onClose - Callback when sheet closes
 * @param props.onUpdate - Callback when user is updated
 * @param props.canEdit - Whether user has write:users permission
 * @returns The RBAC sheet component
 */
export function RbacSheet({ user, onClose, onUpdate, canEdit = false }: RbacSheetProps) {
  const [loading, setLoading] = useState(false);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [availableRoles, setAvailableRoles] = useState<{ id: number; name: string }[]>([]);
  const [isActive, setIsActive] = useState(user.is_active);
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user.roles || []);

  useEffect(() => {
    getRoles()
      .then(setAvailableRoles)
      .catch(err => {
        console.error("Failed to load roles:", err);
        // Fallback to hardcoded roles if API fails
        setAvailableRoles([
          { id: 1, name: "admin" },
          { id: 2, name: "custodian" },
          { id: 3, name: "user" },
        ]);
      })
      .finally(() => setRolesLoading(false));
  }, []);

  const toggleRole = (roleName: string) => {
    setSelectedRoles(prev => (prev.includes(roleName) ? prev.filter(r => r !== roleName) : [...prev, roleName]));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const updated = await updateUser(user.id, { is_active: isActive, roles: selectedRoles });
      onUpdate(updated);
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop overlay */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity" onClick={onClose} />

      {/* Side Panel (Sheet) */}
      <div className="relative w-full max-w-sm h-full bg-background border-l shadow-2xl p-6 flex flex-col gap-6 animate-in slide-in-from-right overflow-y-auto">
        <div className="flex items-center justify-between border-b pb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-semibold">User Access Control</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-full transition-colors text-muted-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Identity Info */}
          <div className="bg-accent/30 p-4 rounded-lg space-y-3">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Email Account</p>
              <p className="font-medium truncate" title={user.email}>
                {user.email}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Display Name</p>
              <p className="font-medium text-sm">{user.display_name || "Anonymous User"}</p>
            </div>
          </div>

          {/* Account Status */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground border-b pb-2">
              Status
            </h3>
            <label className="flex items-start gap-3 cursor-pointer group">
              <div className="relative flex items-center h-5">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={e => setIsActive(e.target.checked)}
                  className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
                />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-sm group-hover:text-primary transition-colors">Active Account</span>
                <span className="text-xs text-muted-foreground">
                  If disabled, the user cannot authenticate or perform any actions.
                </span>
              </div>
            </label>
          </div>

          {/* Role Assignments */}
          <div className="space-y-3">
            <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground border-b pb-2">
              Privileges & Roles
            </h3>
            {rolesLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Loading roles...</span>
              </div>
            ) : (
              <div className="space-y-3 mt-2">
                {availableRoles.map(role => (
                  <label key={role.id} className="flex items-start gap-3 cursor-pointer group">
                    <div className="relative flex items-center h-5">
                      <input
                        type="checkbox"
                        checked={selectedRoles.includes(role.name)}
                        onChange={() => toggleRole(role.name)}
                        className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="font-medium text-sm capitalize group-hover:text-primary transition-colors">
                        {role.name}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Actions Footer */}
        <div className="mt-auto flex justify-end gap-3 pt-6 border-t bg-background">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border hover:bg-accent rounded-md transition-colors font-medium"
          >
            Cancel
          </button>
          {canEdit && (
            <button
              onClick={handleSave}
              disabled={loading || rolesLoading}
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md flex items-center gap-2 font-medium hover:opacity-90 disabled:opacity-50"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Permissions
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
