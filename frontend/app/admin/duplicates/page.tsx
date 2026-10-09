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

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useProfile } from "@/lib/api/hooks";
import { Loader2 } from "lucide-react";
import { DuplicateReviewer } from "@/components/admin/duplicate-reviewer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { Footer } from "@/components/dashboard/footer";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { PermissionName } from "@/lib/permissions";

/**
 * Duplicate review page.
 *
 * @returns The duplicate review page component
 */
export default function DuplicatesPage() {
  const { data: profile, isLoading } = useProfile();
  const router = useRouter();

  const permissions = profile?.permissions ?? [];
  const hasPermission = (perm: PermissionName): boolean => permissions.includes(perm);
  // Duplicate review is a custodian surface: the backend mutation endpoints all
  // require write:metadata, which the contributor role holds and standard users
  // do not.  Guard on the same permission so the page and the API agree -- note
  // this matches the "Metadata" gate in the sibling admin pages, and is
  // deliberately stricter than read:metadata, which every standard user has.
  const canViewMetadata = hasPermission(PermissionName.WRITE_METADATA);

  // Redirect to login when unauthenticated, or to /profile when the viewer has
  // no custodian access.  The sidebar link is only a convenience; this is the
  // actual access boundary, matching the other admin pages.
  useEffect(() => {
    if (isLoading) return;
    if (!profile) {
      router.push("/login");
    } else if (!canViewMetadata) {
      router.push("/profile");
    }
  }, [profile, isLoading, canViewMetadata, router]);

  if (isLoading || !profile || !canViewMetadata) {
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
        <AdminSidebar activeTab="duplicates" />

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 pb-20">
          <div className="flex flex-col gap-8">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Duplicate Review</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Compare flagged Works, Expressions, and Manifestations side by side, then keep the richer record or
                dismiss the false positive. Merging is permanent and re-parents every child onto the surviving entity.
              </p>
            </div>
            <DuplicateReviewer canEdit={canViewMetadata} />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
