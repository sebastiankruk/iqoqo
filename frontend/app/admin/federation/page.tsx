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
import { Activity, Building2, Loader2, Settings, ShieldAlert } from "lucide-react";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { FederationInstancesManager } from "@/components/admin/federation-instances";
import { FederationActivityLog } from "@/components/admin/federation-activity";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { PermissionName } from "@/lib/permissions";
import { Button } from "@/components/ui/button";

/**
 * Admin Federation dashboard page providing peer instance management,
 * activity pipeline logs, and federation settings.
 *
 * @returns Federation administration page component.
 */
export default function FederationAdminPage() {
  const { data: profile, isLoading } = useProfile();
  const [activeTab, setActiveTab] = useState<"instances" | "activity" | "settings">("instances");

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  const permissions = profile.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);
  const canConfigFederation = hasPermission(PermissionName.CONFIG_FEDERATION);

  if (!canConfigFederation) {
    return (
      <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
          <AdminSidebar activeTab="federation" />
          <div className="flex-1 min-w-0 pb-20">
            <div className="p-8 border border-destructive/20 rounded-xl bg-destructive/5 text-center space-y-3">
              <ShieldAlert className="h-8 w-8 text-destructive mx-auto" />
              <h2 className="text-lg font-semibold">Access Restricted</h2>
              <p className="text-sm text-muted-foreground">
                You do not have the <code className="font-mono text-xs">config:federation</code> permission required to
                manage ActivityPub federation settings.
              </p>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <AdminSidebar activeTab="federation" />

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          <div className="flex flex-col gap-6">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Federation Management</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Oversee connected Fediverse library peers, trust policies, and the ActivityPub activity pipeline.
              </p>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-border pb-3">
              <Button
                variant={activeTab === "instances" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setActiveTab("instances")}
                className="flex items-center gap-2"
              >
                <Building2 className="h-4 w-4" />
                Peer Instances
              </Button>
              <Button
                variant={activeTab === "activity" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setActiveTab("activity")}
                className="flex items-center gap-2"
              >
                <Activity className="h-4 w-4" />
                Activity Pipeline Log
              </Button>
              <Button
                variant={activeTab === "settings" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setActiveTab("settings")}
                className="flex items-center gap-2"
              >
                <Settings className="h-4 w-4" />
                Federation Settings
              </Button>
            </div>

            {/* Tab Panes */}
            {activeTab === "instances" && <FederationInstancesManager />}
            {activeTab === "activity" && <FederationActivityLog />}
            {activeTab === "settings" && <InstanceSettings category="federation" />}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
