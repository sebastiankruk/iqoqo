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

import { useProfile } from "@/lib/api/hooks";
import { Loader2 } from "lucide-react";
import { GroupManagement } from "@/components/admin/group-management";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { PermissionName } from "@/lib/permissions";

/**
 * Roles management page.
 *
 * @returns The roles page component
 */
export default function GroupsPage() {
  const { data: profile, isLoading } = useProfile();

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  const permissions = profile.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);
  const canEditRoles = hasPermission(PermissionName.WRITE_ROLES);

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <AdminSidebar activeTab="roles" />

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          <div className="flex flex-col gap-8">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Roles Management</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Configure roles and their assigned permissions for this instance.
              </p>
            </div>
            <GroupManagement canEdit={canEditRoles} />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
