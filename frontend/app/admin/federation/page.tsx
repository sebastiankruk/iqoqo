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
import { FederationInstances } from "@/components/admin/federation-instances";
import { FederationActivityLog } from "@/components/admin/federation-activity";
import { InstanceSettings } from "@/components/admin/instance-settings";

type FederationTab = "instances" | "activity" | "settings";

/**
 * Admin federation management page.
 * @returns {JSX.Element} The component
 */
export default function FederationPage() {
  const [activeTab, setActiveTab] = useState<FederationTab>("instances");

  const tabs: { id: FederationTab; label: string }[] = [
    { id: "instances", label: "Instances" },
    { id: "activity", label: "Activity Log" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Federation</h1>
        <p className="text-muted-foreground">Manage ActivityPub federation with other iqoqo instances.</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "instances" && <FederationInstances />}
        {activeTab === "activity" && <FederationActivityLog />}
        {activeTab === "settings" && <InstanceSettings category="federation" />}
      </div>
    </div>
  );
}
