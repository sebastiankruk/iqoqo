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
import { Loader2, Settings, Users, User, Shield, BadgeCheck } from "lucide-react";
import { GroupManagement } from "@/components/admin/group-management";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

interface NavItemProps {
  label: string;
  icon: LucideIcon;
  isActive: boolean;
  onClick: () => void;
  href?: string;
}

/**
 * Navigation item for settings sidebar.
 * @param props - Navigation item properties
 * @param props.label - Display label
 * @param props.icon - Lucide icon component
 * @param props.isActive - Whether this item is currently active
 * @param props.onClick - Click handler
 * @param props.href - Optional href for external navigation
 * @returns Navigation item component
 */
function NavItem({ label, icon: Icon, isActive, onClick, href }: NavItemProps) {
  const content = (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
        isActive ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}

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

  const isAdmin = profile.roles?.includes("admin");
  const permissions = profile.permissions ?? [];
  const hasPermission = (perm: string): boolean => permissions.includes(perm);
  const canViewRoles = hasPermission("read:roles");
  const canEditRoles = hasPermission("write:roles");

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <aside className="w-full md:w-64 shrink-0 flex flex-col gap-8">
          <div>
            <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Personal</h2>
            <nav className="flex flex-col gap-1">
              <NavItem label="Profile" icon={User} isActive={false} onClick={() => {}} href="/admin/settings" />
            </nav>
          </div>

          {isAdmin && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Administration</h2>
              <nav className="flex flex-col gap-1">
                <NavItem label="Settings" icon={Settings} isActive={false} onClick={() => {}} href="/admin/settings" />
                <NavItem label="Users" icon={Users} isActive={false} onClick={() => {}} href="/admin/settings" />
                {canViewRoles && (
                  <NavItem label="Roles" icon={BadgeCheck} isActive={true} onClick={() => {}} href="/admin/groups" />
                )}
                <NavItem label="Security" icon={Shield} isActive={false} onClick={() => {}} href="/admin/settings" />
              </nav>
            </div>
          )}
        </aside>

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
