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
// Shared administrative sidebar.
//
// This block was previously duplicated across four admin pages, and the copies
// had already drifted apart: the settings and content pages offered "User
// Requests" and "LOD Reconciliation" and called the API section "API
// Integrations", while the groups and duplicates pages omitted the first two
// and called it "API Keys".  A sidebar that shows different links depending on
// which admin page you landed on is a navigation bug, not a cosmetic one, so the
// permission logic and the item list now live here exactly once.

"use client";

import Link from "next/link";
import {
  BadgeCheck,
  Building2,
  Code2,
  CopyCheck,
  Database,
  DollarSign,
  Image as ImageIcon,
  Key,
  LifeBuoy,
  Network,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface NavItemProps {
  label: string;
  icon: LucideIcon;
  isActive: boolean;
  onClick: () => void;
  href?: string;
}

/**
 * Navigation item for the admin sidebar.
 *
 * @param props - Navigation item properties
 * @param props.label - Display label
 * @param props.icon - Lucide icon component
 * @param props.isActive - Whether this item is the current view
 * @param props.onClick - Click handler
 * @param props.href - When set, the item links to another page instead of
 *   switching a tab in place
 * @returns Navigation item component
 */
function NavItem({ label, icon: Icon, isActive, onClick, href }: NavItemProps) {
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
      <Link href={href} className={className} onClick={onClick}>
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

export interface AdminSidebarProps {
  /** Tab currently displayed by the hosting page, if it hosts tabs. */
  activeTab?: string;
  /** Handler for items that switch a tab in place. Defaults to a no-op. */
  onTabChange?: (tab: string) => void;
}

/**
 * The administrative sidebar, shared by every admin page.
 *
 * Reads the viewer's own profile, so permission gating cannot drift between
 * pages.  Pages without tabs (duplicate review, SPARQL explorer) render it with
 * no props.
 *
 * @param props - Component props
 * @param props.activeTab - Tab currently displayed by the hosting page
 * @param props.onTabChange - Handler for in-place tab switches
 * @returns The admin sidebar
 */
export function AdminSidebar({ activeTab, onTabChange }: AdminSidebarProps) {
  const { data: profile } = useProfile();

  const permissions = profile?.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);

  const canViewMetadata = hasPermission(PermissionName.WRITE_METADATA);
  const canEditCover = hasPermission(PermissionName.EDIT_COVER);
  const canViewEscalationQueue = hasPermission(PermissionName.ESCALATE_RESOLVE);
  const canViewUsers = hasPermission(PermissionName.READ_USERS);
  const canViewRoles = hasPermission(PermissionName.READ_ROLES);
  const canAccessSparql =
    hasPermission(PermissionName.READ_METADATA) ||
    hasPermission(PermissionName.WRITE_METADATA) ||
    (profile?.roles ?? []).includes("admin") ||
    (profile?.roles ?? []).includes("contributor");
  const canViewSettings =
    hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) ||
    hasPermission(PermissionName.CONFIG_FEDERATION) ||
    hasPermission(PermissionName.CONFIG_AFFILIATE) ||
    hasPermission(PermissionName.CONFIG_INTERNAL);

  const hasCustodianAccess = canViewMetadata || canEditCover || canViewEscalationQueue || canAccessSparql;

  const selectTab = (tab: string) => onTabChange?.(tab);
  // Link items carry a real href, so the browser navigates; the click handler
  // only exists to satisfy the shared NavItem signature.
  const noop = () => {};

  return (
    <aside className="w-full md:w-64 shrink-0 flex flex-col gap-8">
      {hasCustodianAccess && (
        <div>
          <h2 className="text-sm font-semibold text-foreground mb-3 px-3">Custodians</h2>
          <nav className="flex flex-col gap-1">
            {canViewMetadata && (
              <NavItem
                label="Metadata"
                icon={Database}
                isActive={activeTab === "metadata"}
                onClick={() => selectTab("metadata")}
                href="/admin/content?tab=metadata"
              />
            )}
            {canViewMetadata && (
              <NavItem
                label="Duplicate Review"
                icon={CopyCheck}
                isActive={activeTab === "duplicates"}
                onClick={noop}
                href="/admin/duplicates"
              />
            )}
            {canEditCover && (
              <NavItem
                label="Cover Art"
                icon={ImageIcon}
                isActive={activeTab === "cover-art"}
                onClick={() => selectTab("cover-art")}
                href="/admin/content?tab=cover-art"
              />
            )}
            {canViewEscalationQueue && (
              <NavItem
                label="User Requests"
                icon={LifeBuoy}
                isActive={activeTab === "escalations"}
                onClick={() => selectTab("escalations")}
                href="/admin/content?tab=escalations"
              />
            )}
            {canAccessSparql && (
              <NavItem
                label="SPARQL Explorer"
                icon={Code2}
                isActive={activeTab === "sparql"}
                onClick={noop}
                href="/admin/sparql"
              />
            )}
            <NavItem
              label="LOD Reconciliation"
              icon={Network}
              isActive={activeTab === "lod"}
              onClick={noop}
              href="/admin/lod"
            />
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
              isActive={activeTab === "instance"}
              onClick={() => selectTab("instance")}
            />
            {hasPermission(PermissionName.CONFIG_FEDERATION) && (
              <NavItem
                label="Federation"
                icon={Building2}
                isActive={activeTab === "federation"}
                onClick={() => selectTab("federation")}
              />
            )}
            {hasPermission(PermissionName.CONFIG_AFFILIATE) && (
              <NavItem
                label="Monetization"
                icon={DollarSign}
                isActive={activeTab === "monetization"}
                onClick={() => selectTab("monetization")}
              />
            )}
            {hasPermission(PermissionName.CONFIG_EXTERNAL_APIS) && (
              <NavItem
                label="API Integrations"
                icon={Key}
                isActive={activeTab === "apikeys"}
                onClick={() => selectTab("apikeys")}
              />
            )}
            {canViewUsers && (
              <NavItem label="Users" icon={Users} isActive={activeTab === "users"} onClick={() => selectTab("users")} />
            )}
            {canViewRoles && (
              <NavItem
                label="Roles"
                icon={BadgeCheck}
                isActive={activeTab === "roles"}
                onClick={() => selectTab("roles")}
                href="/admin/groups"
              />
            )}
            {hasPermission(PermissionName.CONFIG_INTERNAL) && (
              <NavItem
                label="Security"
                icon={Shield}
                isActive={activeTab === "security"}
                onClick={() => selectTab("security")}
              />
            )}
          </nav>
        </div>
      )}
    </aside>
  );
}
