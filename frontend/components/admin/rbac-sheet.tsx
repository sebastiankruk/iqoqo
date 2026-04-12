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
import { AdminUser, updateUser } from "@/lib/api/admin";
import { Loader2, X, ShieldAlert } from "lucide-react";

interface RbacSheetProps {
  /** The user to edit */
  user: AdminUser;
  /** Callback when sheet closes */
  onClose: () => void;
  /** Callback when user is updated */
  onUpdate: (updated: AdminUser) => void;
}

// Available base system roles
const AVAILABLE_ROLES = ["admin", "custodian", "user"];

/**
 * Slide-over interface for managing user properties and RBAC assignments.
 *
 * @param props - Component props
 * @param props.user - The user to edit
 * @param props.onClose - Callback when sheet closes
 * @param props.onUpdate - Callback when user is updated
 * @returns The RBAC sheet component
 */
export function RbacSheet({ user, onClose, onUpdate }: RbacSheetProps) {
  const [loading, setLoading] = useState(false);
  const [isActive, setIsActive] = useState(user.is_active);
  const [roles, setRoles] = useState<string[]>(user.roles || []);

  const toggleRole = (role: string) => {
    setRoles(prev => (prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const updated = await updateUser(user.id, { is_active: isActive, roles });
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
            <div className="space-y-3 mt-2">
              {AVAILABLE_ROLES.map(role => (
                <label key={role} className="flex items-start gap-3 cursor-pointer group">
                  <div className="relative flex items-center h-5">
                    <input
                      type="checkbox"
                      checked={roles.includes(role)}
                      onChange={() => toggleRole(role)}
                      className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary"
                    />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-medium text-sm capitalize group-hover:text-primary transition-colors">
                      {role}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {role === "admin" && "Full system access including configuration."}
                      {role === "custodian" && "Manage collections, metadata, and approvals."}
                      {role === "user" && "Standard permissions to maintain a personal collection."}
                    </span>
                  </div>
                </label>
              ))}
            </div>
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
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md flex items-center gap-2 font-medium hover:opacity-90 disabled:opacity-50"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Permissions
          </button>
        </div>
      </div>
    </div>
  );
}
