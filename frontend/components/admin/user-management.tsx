"use client";

import { useState, useEffect } from "react";
import { getUsers } from "@/lib/api/admin";
import { Loader2 } from "lucide-react";

export function UserManagement() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUsers()
      .then(setUsers)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4 flex justify-center"><Loader2 className="animate-spin" /></div>;

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
          {users.map((u) => (
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
