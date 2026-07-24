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
import { useSearchParams } from "next/navigation";
import { useProfile } from "@/lib/api/hooks";
import {
  Loader2,
  Settings,
  Users,
  User,
  Shield,
  BadgeCheck,
  Key,
  Building2,
  DollarSign,
  Database,
  Search,
  X,
  Image as ImageIcon,
  LifeBuoy,
} from "lucide-react";
import { PermissionName } from "@/lib/permissions";
import { InstanceSettings } from "@/components/admin/instance-settings";
import { UserManagement } from "@/components/admin/user-management";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import { EscalationQueue } from "@/components/admin/escalation-queue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { searchFrbrEntities, type FrbrSearchResult } from "@/lib/api/admin";
import { CoverArtEditorWrapper } from "@/components/admin/cover-editor/cover-art-editor-wrapper";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import type React from "react";
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
 *
 * @param props - Navigation item properties
 * @param props.label - Display label
 * @param props.icon - Lucide icon component
 * @param props.isActive - Whether this item is currently active
 * @param props.onClick - Click handler
 * @param props.href - Optional href for external navigation
 * @returns Navigation item JSX element
 */
function NavItem({ label, icon: Icon, isActive, onClick, href }: NavItemProps): React.JSX.Element {
  const className = cn(
    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
    isActive ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
  );

  const content = (
    <>
      <Icon className="h-4 w-4" />
      {label}
    </>
  );

  if (href) {
    return (
      <Link href={href} onClick={onClick} className={className}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      {content}
    </button>
  );
}

/**
 * Inner content component that uses useSearchParams.
 * Must be wrapped in Suspense boundary.
 * @returns Content management page JSX element
 */
function ContentManagementContent(): React.JSX.Element {
  const searchParams = useSearchParams();
  const { data: profile, isLoading: profileLoading } = useProfile();
  const [internalTab, setInternalTab] = useState<string | null>(null);

  const handleTabChange = (tab: string) => {
    setInternalTab(tab);
  };

  const manifId = searchParams.get("manifestationId");
  const preselectedManifestationId = (() => {
    if (manifId) {
      const id = parseInt(manifId, 10);
      if (!isNaN(id)) {
        return id;
      }
    }
    return null;
  })();

  const activeTab = internalTab || searchParams.get("tab") || "profile";
  const effectiveTab = activeTab;

  const permissions = profile?.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);

  const canViewSettings =
    hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) ||
    hasPermission(PermissionName.CONFIG_FEDERATION) ||
    hasPermission(PermissionName.CONFIG_AFFILIATE) ||
    hasPermission(PermissionName.CONFIG_INTERNAL);
  const canViewUsers = hasPermission(PermissionName.READ_USERS);
  const canViewRoles = hasPermission(PermissionName.READ_ROLES);
  const canEditUsers = hasPermission(PermissionName.WRITE_USERS);
  const canViewMetadata = hasPermission(PermissionName.WRITE_METADATA);
  const canEditCover = hasPermission(PermissionName.EDIT_COVER);
  const canViewEscalationQueue = hasPermission(PermissionName.ESCALATE_RESOLVE);

  const hasCustodianAccess = canViewMetadata || canEditCover || canViewEscalationQueue;

  // Auto-select first available custodian tab when landing with no explicit tab
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (!tabParam && !internalTab && profile && hasCustodianAccess) {
      if (canViewMetadata) {
        setInternalTab("metadata");
      } else if (canEditCover) {
        setInternalTab("cover-art");
      } else if (canViewEscalationQueue) {
        setInternalTab("escalations");
      }
    }
    // Only run on mount when profile first loads
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile, hasCustodianAccess]);

  if (profileLoading || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

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

          {hasCustodianAccess && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Custodians</h2>
              <nav className="flex flex-col gap-1">
                {canViewMetadata && (
                  <NavItem
                    label="Metadata"
                    icon={Database}
                    isActive={effectiveTab === "metadata"}
                    onClick={() => handleTabChange("metadata")}
                  />
                )}
                {canEditCover && (
                  <NavItem
                    label="Cover Art"
                    icon={ImageIcon}
                    isActive={effectiveTab === "cover-art"}
                    onClick={() => handleTabChange("cover-art")}
                  />
                )}
                {canViewEscalationQueue && (
                  <NavItem
                    label="User Requests"
                    icon={LifeBuoy}
                    isActive={effectiveTab === "escalations"}
                    onClick={() => handleTabChange("escalations")}
                  />
                )}
              </nav>
            </div>
          )}

          {canViewSettings && (
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Administration</h2>
              <nav className="flex flex-col gap-1">
                <NavItem
                  label="Settings"
                  icon={Settings}
                  isActive={effectiveTab === "instance"}
                  onClick={() => handleTabChange("instance")}
                />
                {hasPermission(PermissionName.CONFIG_FEDERATION) && (
                  <NavItem
                    label="Federation"
                    icon={Building2}
                    isActive={effectiveTab === "federation"}
                    onClick={() => handleTabChange("federation")}
                  />
                )}
                {hasPermission(PermissionName.CONFIG_AFFILIATE) && (
                  <NavItem
                    label="Monetization"
                    icon={DollarSign}
                    isActive={effectiveTab === "monetization"}
                    onClick={() => handleTabChange("monetization")}
                  />
                )}
                {hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) && (
                  <NavItem
                    label="API Integrations"
                    icon={Key}
                    isActive={effectiveTab === "apikeys"}
                    onClick={() => handleTabChange("apikeys")}
                  />
                )}
                <NavItem
                  label="Users"
                  icon={Users}
                  isActive={effectiveTab === "users"}
                  onClick={() => handleTabChange("users")}
                />
                {canViewRoles && (
                  <NavItem
                    label="Roles"
                    icon={BadgeCheck}
                    isActive={effectiveTab === "roles"}
                    onClick={() => handleTabChange("roles")}
                    href="/admin/groups"
                  />
                )}
                {hasPermission(PermissionName.CONFIG_INTERNAL) && (
                  <NavItem
                    label="Security"
                    icon={Shield}
                    isActive={effectiveTab === "security"}
                    onClick={() => handleTabChange("security")}
                  />
                )}
              </nav>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <section className="flex-1">
          {effectiveTab === "profile" && (
            <Card>
              <CardHeader>
                <CardTitle>Profile Settings</CardTitle>
                <CardDescription>Manage your personal account settings</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Profile settings coming soon...</p>
              </CardContent>
            </Card>
          )}

          {effectiveTab === "instance" && canViewSettings && <InstanceSettings />}

          {effectiveTab === "users" && canViewUsers && <UserManagement canEdit={canEditUsers} />}

          {effectiveTab === "groups" && canViewRoles && <GroupManagementWrapper />}

          {effectiveTab === "metadata" && canViewMetadata && (
            <ContentEditorWrapper preselectedManifestationId={preselectedManifestationId} />
          )}

          {effectiveTab === "cover-art" && canEditCover && (
            <CoverArtEditorWrapper preselectedManifestationId={preselectedManifestationId} />
          )}

          {effectiveTab === "escalations" && canViewEscalationQueue && <EscalationQueue />}
        </section>
      </main>

      <Footer />
    </div>
  );
}

/**
 * Wrapper for Content Editor with search functionality.
 * @param root0 - The props object
 * @param root0.preselectedManifestationId - Optional preselected manifestation ID
 * @returns Content editor with search JSX element
 */
function ContentEditorWrapper({
  preselectedManifestationId,
}: {
  preselectedManifestationId?: number | null;
}): React.JSX.Element {
  const [selectedManifestationId, setSelectedManifestationId] = useState<number | null>(
    preselectedManifestationId ?? null
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FrbrSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setHasSearched(true);

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

  useEffect(() => {
    if (searchResults.length === 1 && !selectedManifestationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedManifestationId(searchResults[0].id);
    }
  }, [searchResults, selectedManifestationId]);

  const handleSelectManifestation = (id: number) => {
    setSelectedManifestationId(id);
  };

  const handleClearSelection = () => {
    setSelectedManifestationId(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">FRBR Content Editor</h1>
        <p className="text-muted-foreground mt-2">
          Manage Works, Expressions, and Manifestations directly through the hierarchy.
        </p>
      </div>

      {!selectedManifestationId ? (
        <Card>
          <CardHeader>
            <CardTitle>Find Manifestation</CardTitle>
            <CardDescription>
              Search by ISBN-13, UPC, EAN, Title, or Author to locate the manifestation you want to edit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <input
                placeholder="Enter ISBN-13, UPC, EAN, Title, or Author"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 max-w-md"
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

            {hasSearched && searchResults.length === 0 && !searching && !searchError && (
              <p className="text-muted-foreground mt-4">No results found. Try a different search term.</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Editing Manifestation #{selectedManifestationId}</CardTitle>
              <CardDescription>Navigate through the FRBR hierarchy using the tabs below.</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={handleClearSelection}>
              <X className="h-4 w-4 mr-2" />
              Close
            </Button>
          </CardHeader>
          <CardContent>
            <FrbrEditor manifestationId={selectedManifestationId} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * Wrapper for GroupManagement component.
 * @returns Group management component JSX element
 */
function GroupManagementWrapper(): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Groups & Roles</CardTitle>
        <CardDescription>Manage user roles and their permissions</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">Group management coming soon...</p>
      </CardContent>
    </Card>
  );
}

/**
 * Main settings page component with Suspense boundary.
 * @returns Settings page JSX element
 */
export default function ContentManagementPage(): React.JSX.Element {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="animate-spin h-8 w-8" />
        </div>
      }
    >
      <ContentManagementContent />
    </Suspense>
  );
}
