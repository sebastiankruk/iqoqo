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
import { getUsers } from "@/lib/api/admin";
import { Loader2 } from "lucide-react";

/**
 * Admin user details
 */
interface AdminUser {
  id: string;
  email: string;
  display_name?: string | null;
  roles?: string[];
  is_active?: boolean;
}

/**
 * Component for managing users.
 *
 * @returns {JSX.Element} The component
 */
export function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUsers()
      // Double cast via unknown to satisfy TypeScript's overlap rules
      .then(data => setUsers(data as unknown as AdminUser[]))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="p-4 flex justify-center">
        <Loader2 className="animate-spin" />
      </div>
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border-collapse">
        <thead className="text-xs uppercase bg-accent/50 text-accent-foreground">
          <tr>
            <th className="px-6 py-3 rounded-tl-md">Email</th>
            <th className="px-6 py-3">Display Name</th>
            <th className="px-6 py-3">Roles</th>
            <th className="px-6 py-3 rounded-tr-md">Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} className="border-b dark:border-white/10 hover:bg-accent/20 transition-colors">
              <td className="px-6 py-4 font-medium">{u.email}</td>
              <td className="px-6 py-4">{u.display_name}</td>
              <td className="px-6 py-4">
                <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                  {u.roles?.join(", ") || "user"}
                </span>
              </td>
              <td className="px-6 py-4">{u.is_active ? "Active" : "Inactive"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
