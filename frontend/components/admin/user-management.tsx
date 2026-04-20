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

import { useState, useEffect, useCallback } from "react";
import { getUsers, AdminUser } from "@/lib/api/admin";
import { Loader2, Search, Filter } from "lucide-react";
import { RbacSheet } from "./rbac-sheet";

interface UserManagementProps {
  canEdit?: boolean;
}

/**
 * Component for managing users, displaying data table with search/filtering
 * and invoking the RBAC Sheet.
 *
 * @param props - Component props
 * @param props.canEdit - Whether user has write:users permission
 * @returns {JSX.Element} The component
 */
export function UserManagement({ canEdit = false }: UserManagementProps) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getUsers({ search: searchQuery, status: statusFilter });
      setUsers(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter]);

  // Debounced search effect
  useEffect(() => {
    const handler = setTimeout(() => fetchUsers(), 300);
    return () => clearTimeout(handler);
  }, [fetchUsers]);

  const handleUserUpdate = (updatedUser: AdminUser) => {
    setUsers(prev => prev.map(u => (u.id === updatedUser.id ? updatedUser : u)));
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="search"
            placeholder="Search users..."
            className="w-full pl-9 pr-4 py-2 text-sm border rounded-md bg-background focus:ring-1 focus:ring-primary outline-none"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="relative w-full sm:w-auto flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="border rounded-md py-2 px-3 text-sm bg-background outline-none"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Suspended</option>
          </select>
        </div>
      </div>

      <div className="border rounded-md overflow-x-auto bg-card border-border/50">
        <table className="w-full text-sm text-left border-collapse">
          <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border/50">
            <tr>
              <th className="px-6 py-4 font-semibold">Email</th>
              <th className="px-6 py-4 font-semibold">Display Name</th>
              <th className="px-6 py-4 font-semibold">Roles</th>
              <th className="px-6 py-4 font-semibold text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr>
                <td colSpan={4} className="py-12 text-center text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-muted-foreground">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map(u => (
                <tr
                  key={u.id}
                  onClick={canEdit ? () => setSelectedUser(u) : undefined}
                  className={canEdit ? "hover:bg-muted/30 transition-colors cursor-pointer" : ""}
                >
                  <td className="px-6 py-4 font-medium">{u.email}</td>
                  <td className="px-6 py-4 text-muted-foreground">{u.display_name || "—"}</td>
                  <td className="px-6 py-4 flex gap-2 flex-wrap">
                    {u.roles && u.roles.length > 0 ? (
                      u.roles.map(role => (
                        <span
                          key={role}
                          className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full capitalize"
                        >
                          {role}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground text-xs">User</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span
                      className={
                        u.is_active
                          ? "px-2 py-1 text-xs rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-200 dark:ring-emerald-900"
                          : "px-2 py-1 text-xs rounded-full bg-destructive/10 text-destructive ring-1 ring-destructive/20"
                      }
                    >
                      {u.is_active ? "Active" : "Suspended"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedUser && (
        <RbacSheet
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
          onUpdate={handleUserUpdate}
          canEdit={canEdit}
        />
      )}
    </div>
  );
}
