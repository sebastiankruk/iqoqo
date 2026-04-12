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
import { useProfile } from "@/lib/api/hooks";
import { Loader2, Settings, Users, User, Shield } from "lucide-react";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { UserManagement } from "@/components/admin/user-management";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface NavItemProps {
  /** Display label */
  label: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Whether this item is currently active */
  isActive: boolean;
  /** Click handler */
  onClick: () => void;
}

/**
 * Navigation item for settings sidebar.
 * @param props - Navigation item properties
 * @param props.label - Display label
 * @param props.icon - Lucide icon component
 * @param props.isActive - Whether this item is currently active
 * @param props.onClick - Click handler
 * @returns Navigation item component
 */
function NavItem({ label, icon: Icon, isActive, onClick }: NavItemProps) {
  return (
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
}

/**
 * Unified settings hub page - serves as Profile for regular users and Admin panel for administrators.
 *
 * @returns {JSX.Element} The settings hub page component
 */
export default function SettingsHubPage() {
  const { data: profile, isLoading } = useProfile();

  const [activeTab, setActiveTab] = useState("profile");

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  const isAdmin = profile.roles?.includes("admin");

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <aside className="w-full md:w-64 shrink-0 flex flex-col gap-8">
          <div>
            <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Personal</h2>
            <nav className="flex flex-col gap-1">
              <NavItem
                label="Profile Overview"
                icon={User}
                isActive={activeTab === "profile"}
                onClick={() => setActiveTab("profile")}
              />
            </nav>
          </div>

          {isAdmin && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Administration</h2>
              <nav className="flex flex-col gap-1">
                <NavItem
                  label="Instance Settings"
                  icon={Settings}
                  isActive={activeTab === "instance"}
                  onClick={() => setActiveTab("instance")}
                />
                <NavItem
                  label="User Management"
                  icon={Users}
                  isActive={activeTab === "users"}
                  onClick={() => setActiveTab("users")}
                />
                <NavItem
                  label="API & Security"
                  icon={Shield}
                  isActive={activeTab === "security"}
                  onClick={() => setActiveTab("security")}
                />
              </nav>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          {activeTab === "profile" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Profile Settings</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage your personal account settings and preferences.
                </p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <h3 className="text-lg font-medium">Display Name</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This is your public display name on this instance.
                  </p>
                  <input
                    className="mt-4 flex h-9 w-full max-w-md rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={profile.display_name || ""}
                    readOnly
                  />
                </div>
                <div className="bg-muted/40 dark:bg-white/[0.02] border-t border-border dark:border-white/10 px-6 py-3 flex justify-end">
                  <button className="h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm font-medium">
                    Save
                  </button>
                </div>
              </div>
            </div>
          )}

          {isAdmin && activeTab === "instance" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Instance Settings</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage global configuration, federation, and monetization for your node.
                </p>
              </div>
              <InstanceSettings />
            </div>
          )}

          {isAdmin && activeTab === "users" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">User Management</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  View and manage roles for users registered on this instance.
                </p>
              </div>
              <UserManagement />
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
