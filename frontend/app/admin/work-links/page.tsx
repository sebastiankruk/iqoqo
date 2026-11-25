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

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { WorkLinkReviewer } from "@/components/admin/work-link-reviewer";
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";
import { useProfile } from "@/lib/api/hooks";
import { PermissionName } from "@/lib/permissions";

/**
 * Custodian cross-media FRBR Work linking and reconciliation page.
 */
export default function WorkLinksPage() {
  const { data: profile, isLoading } = useProfile();
  const router = useRouter();
  const t = useTranslations("workLinks");

  const permissions = profile?.permissions ?? [];
  const canEditMetadata = permissions.includes(PermissionName.WRITE_METADATA);

  useEffect(() => {
    if (isLoading) return;
    if (!profile) {
      router.push("/login");
    } else if (!canEditMetadata) {
      router.push("/profile");
    }
  }, [profile, isLoading, canEditMetadata, router]);

  if (isLoading || !profile || !canEditMetadata) {
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
        <AdminSidebar activeTab="work-links" />

        <div className="flex-1 min-w-0 pb-20">
          <div className="flex flex-col gap-8">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
              <p className="text-sm text-muted-foreground mt-1">{t("subtitle")}</p>
            </div>
            <WorkLinkReviewer canEdit={canEditMetadata} />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
