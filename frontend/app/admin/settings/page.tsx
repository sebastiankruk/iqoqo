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

import { useEffect, useState } from "react";
import { useProfile } from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { UserManagement } from "@/components/admin/user-management";
import { Navbar } from "@/components/dashboard/navbar";
import { Footer } from "@/components/dashboard/footer";

/**
 * Admin settings page component.
 *
 * @returns {JSX.Element} The page component
 */
export default function AdminSettingsPage() {
  const { data: profile, isLoading } = useProfile();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("instance");

  useEffect(() => {
    if (!isLoading && (!profile || !profile.roles?.includes("admin"))) {
      router.push("/"); // Redirect non-admins
    }
  }, [profile, isLoading, router]);

  if (isLoading || !profile) return <div className="flex justify-center p-12"><Loader2 className="animate-spin h-8 w-8" /></div>;

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-6xl mx-auto py-10 px-6">
        <h1 className="text-3xl font-serif font-bold mb-8">Admin Settings</h1>

        <div className="flex flex-col md:flex-row gap-8">
          {/* Sidebar Nav */}
          <aside className="w-full md:w-64 shrink-0">
            <nav className="flex flex-col gap-2">
              <button
                onClick={() => setActiveTab("instance")}
                className={`text-left px-4 py-2 rounded-md ${activeTab === 'instance' ? 'bg-accent text-accent-foreground font-medium' : 'hover:bg-primary-foreground/10'}`}
              >
                Instance Settings
              </button>
              <button
                onClick={() => setActiveTab("users")}
                className={`text-left px-4 py-2 rounded-md ${activeTab === 'users' ? 'bg-accent text-accent-foreground font-medium' : 'hover:bg-primary-foreground/10'}`}
              >
                User Management
              </button>
              <button
                onClick={() => setActiveTab("integrations")}
                className={`text-left px-4 py-2 rounded-md ${activeTab === 'integrations' ? 'bg-accent text-accent-foreground font-medium' : 'hover:bg-primary-foreground/10'}`}
              >
                Integrations & Monetization
              </button>
            </nav>
          </aside>

          {/* Main Content Area */}
          <main className="flex-1 bg-white dark:bg-[#0a0c10] border border-primary/10 dark:border-white/10 rounded-lg p-6">
            {activeTab === "instance" && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Instance Settings</h2>
                <p className="text-sm text-muted-foreground mb-6">Manage global configuration for your iqoqo node.</p>
                <InstanceSettings />
              </div>
            )}
            {activeTab === "users" && (
              <div>
                <h2 className="text-xl font-semibold mb-4">User Management</h2>
                <UserManagement />
              </div>
            )}
            {activeTab === "integrations" && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Integrations & Monetization</h2>
                {/* Add Affiliate IDs / Federation forms here (reuse InstanceSettings inputs if needed) */}
                <InstanceSettings />
              </div>
            )}
          </main>
        </div>
      </main>
      <Footer />
    </div>
  );
}
