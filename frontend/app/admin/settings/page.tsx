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

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useProfile } from "@/lib/api/hooks";
import { Loader2, Search, X } from "lucide-react";
import { PermissionName } from "@/lib/permissions";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { UserManagement } from "@/components/admin/user-management";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { searchFrbrEntities, type FrbrSearchResult } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import type React from "react";

/**
 * Inner settings content component that uses useSearchParams.
 * Must be wrapped in Suspense boundary.
 * @returns Settings page JSX element
 */
function SettingsContent(): React.JSX.Element {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { data: profile, isLoading } = useProfile();
  const [internalTab, setInternalTab] = useState<string | null>(null);

  // Redirect to login if user is unauthenticated, or to /profile if no admin/custodian access
  useEffect(() => {
    if (!isLoading && !profile) {
      router.push("/login");
    } else if (!isLoading && profile) {
      const isAdmin = profile.roles?.includes("admin");
      const permissions = profile.permissions ?? [];
      const hasCustodianPerms = permissions.some(p =>
        ["write:metadata", "edit:cover", "escalate:resolve", "read:metadata"].includes(p)
      );
      if (!isAdmin && !hasCustodianPerms) {
        router.push("/profile");
      }
    }
  }, [profile, isLoading, router]);

  const handleTabChange = (tab: string) => {
    setInternalTab(tab);
  };

  if (isLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  const permissions = profile.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);

  const canViewSettings =
    hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) ||
    hasPermission(PermissionName.CONFIG_FEDERATION) ||
    hasPermission(PermissionName.CONFIG_AFFILIATE) ||
    hasPermission(PermissionName.CONFIG_INTERNAL);
  const canViewUsers = hasPermission(PermissionName.READ_USERS);
  const canEditUsers = hasPermission(PermissionName.WRITE_USERS);
  const canViewMetadata = hasPermission(PermissionName.WRITE_METADATA);
  const canEditCover = hasPermission(PermissionName.EDIT_COVER);
  const canViewEscalationQueue = hasPermission(PermissionName.ESCALATE_RESOLVE);
  const canAccessSparql =
    hasPermission(PermissionName.READ_METADATA) ||
    hasPermission(PermissionName.WRITE_METADATA) ||
    (profile.roles ?? []).includes("admin") ||
    (profile.roles ?? []).includes("contributor");
  const isAdmin = (profile.roles ?? []).includes("admin");

  // Determine default tab based on permissions
  const getDefaultTab = (): string => {
    if (searchParams.get("tab")) return searchParams.get("tab")!;
    if (isAdmin && canViewSettings) return "instance";
    if (canViewMetadata) return "metadata";
    if (canEditCover) return "cover-art";
    if (canViewEscalationQueue) return "escalations";
    if (canAccessSparql) return "sparql";
    return "instance";
  };

  const activeTab = internalTab || getDefaultTab();

  return (
    <div className="min-h-screen bg-background dark:bg-[#040608] flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-12">
        {/* Left Sidebar Navigation */}
        <AdminSidebar activeTab={activeTab} onTabChange={handleTabChange} />

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          {activeTab === "instance" && canViewSettings && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Instance Settings</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Configure instance-wide settings for this deployment.
                </p>
              </div>
              <InstanceSettings category="internal" />
            </div>
          )}

          {activeTab === "federation" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Federation</h1>
                <p className="text-sm text-muted-foreground mt-1">Manage federated instances and partnerships.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "monetization" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Monetization</h1>
                <p className="text-sm text-muted-foreground mt-1">Configure affiliate programs and revenue sharing.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "apikeys" && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">API Integrations</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage external API keys for third-party integrations.
                </p>
              </div>
              <InstanceSettings category="external_apis" showApiKeys />
            </div>
          )}

          {activeTab === "users" && canViewUsers && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">User Management</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  View and manage roles for users registered on this instance.
                </p>
              </div>
              <UserManagement canEdit={canEditUsers} />
            </div>
          )}

          {activeTab === "security" && hasPermission(PermissionName.CONFIG_INTERNAL) && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
                <p className="text-sm text-muted-foreground mt-1">Configure internal security settings.</p>
              </div>
              <div className="border border-border dark:border-white/10 rounded-xl bg-card text-card-foreground shadow-sm overflow-hidden">
                <div className="p-6">
                  <p className="text-sm text-muted-foreground">Coming soon</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "metadata" && canViewMetadata && (
            <div className="flex flex-col gap-8">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">FRBR Metadata Editor</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage Works, Expressions, and Manifestations through the FRBR hierarchy.
                </p>
              </div>
              <FrbrEditorWrapper />
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

/**
 * Unified settings hub page - serves as Profile for regular users and Admin panel for administrators.
 *
 * @returns The settings hub page component
 */
export default function SettingsHubPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}

/**
 * Wrapper for the FRBR Editor that handles manifestation search and selection.
 *
 * @returns The wrapped FRBR Editor component
 */
function FrbrEditorWrapper() {
  const [selectedManifestationId, setSelectedManifestationId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FrbrSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchError(null);
    setSearchResults([]);

    try {
      const results = await searchFrbrEntities(searchQuery.trim(), "manifestation", 20);
      setSearchResults(results);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleSelectManifestation = (id: number) => {
    setSelectedManifestationId(id);
  };

  const handleClearSelection = () => {
    setSelectedManifestationId(null);
  };

  if (!selectedManifestationId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Find Manifestation</CardTitle>
          <CardDescription>
            Search by ISBN-13, UPC, or EAN to locate the manifestation you want to edit.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <input
              placeholder="Enter ISBN-13, UPC, or EAN"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <Button onClick={handleSearch} disabled={searching}>
              {searching ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Search className="h-4 w-4 mr-2" />}
              Search
            </Button>
          </div>

          {searchError && <p className="text-destructive mt-4">{searchError}</p>}

          {searchResults.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium mb-3">Search Results</h3>
              <div className="border rounded-lg divide-y">
                {searchResults.map(result => (
                  <div
                    key={result.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50 cursor-pointer"
                    onClick={() => handleSelectManifestation(result.id)}
                  >
                    <div>
                      <p className="font-medium">{result.title}</p>
                      <p className="text-sm text-muted-foreground">
                        ID: {result.id}
                        {result.isbn13 && ` | ISBN: ${result.isbn13}`}
                        {result.upc && ` | UPC: ${result.upc}`}
                      </p>
                    </div>
                    <Button variant="outline" size="sm">
                      Edit
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {searchResults.length === 0 && !searching && !searchError && searchQuery && (
            <p className="text-muted-foreground mt-4">No results found. Try a different search term.</p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Editing Manifestation #{selectedManifestationId}</CardTitle>
          <CardDescription>Navigate through the FRBR hierarchy using the tabs below.</CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={handleClearSelection}>
          <X className="h-4 w-4 mr-2" />
          Clear
        </Button>
      </CardHeader>
      <CardContent>
        <FrbrEditor manifestationId={selectedManifestationId} />
      </CardContent>
    </Card>
  );
}
