"use client";

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

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Library } from "lucide-react";

import { useResolvedRouteParam } from "@/lib/capacitor/route-params";
import { resolveApiUrl } from "@/lib/utils";
import type { Item, CatalogEntry } from "@/types/frbr";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { PublicProfilePager } from "@/components/public/public-profile-pager";
import { ShareButton } from "@/components/ui/share-button";
import { CheckInventory } from "@/components/public/check-inventory";
import { EmptyState } from "@/components/ui/empty-state";
import { Avatar } from "@/components/ui/avatar";
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";

export interface PublicProfileUser {
  username: string;
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  public_item_count: number;
}

export interface PublicProfileData {
  user: PublicProfileUser;
  items: (Item | CatalogEntry)[];
  meta?: {
    pages?: number;
    total?: number;
  };
  currentPage?: number;
}

interface PublicProfileClientProps {
  initialData?: PublicProfileData | null;
  initialUsername?: string;
}

/**
 * Client-hydrated public profile view for web and native Capacitor shells.
 *
 * @param {PublicProfileClientProps} props - Component props.
 * @returns {JSX.Element} Rendered public profile page.
 */
export function PublicProfileClient({ initialData, initialUsername }: PublicProfileClientProps) {
  const resolvedUsername = useResolvedRouteParam("username") || initialUsername;
  const t = useTranslations("Public");

  const [profileData, setProfileData] = useState<PublicProfileData | null>(initialData || null);
  const currentPage = initialData?.currentPage || 1;
  const [isLoading, setIsLoading] = useState<boolean>(!initialData && !!resolvedUsername);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);

  useEffect(() => {
    if (initialData) return;
    if (!resolvedUsername || resolvedUsername === "_placeholder") return;

    let isMounted = true;

    Promise.all([
      fetch(resolveApiUrl(`/public/u/${resolvedUsername}`, false)),
      fetch(resolveApiUrl(`/public/u/${resolvedUsername}/items?page=${currentPage}&per_page=24`, false)),
    ])
      .then(async ([userRes, itemsRes]) => {
        if (!isMounted) return;
        if (userRes.status === 404) {
          setIsNotFound(true);
          return;
        }
        if (!userRes.ok || !itemsRes.ok) {
          setIsError(true);
          return;
        }
        const userJson = await userRes.json();
        const itemsJson = await itemsRes.json();

        if (userJson.success && userJson.data) {
          setProfileData({
            user: userJson.data,
            items: itemsJson.data?.items || [],
            meta: itemsJson.meta || {},
            currentPage,
          });
        } else {
          setIsError(true);
        }
      })
      .catch(() => {
        if (isMounted) setIsError(true);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [initialData, resolvedUsername, currentPage]);

  if (isNotFound) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16 text-center">
          <h1 className="text-2xl font-serif font-bold">User Not Found</h1>
          <p className="mt-3 text-muted-foreground">The requested user profile does not exist or is private.</p>
        </main>
        <Footer />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16 text-center">
          <h1 className="text-2xl font-serif font-bold">Error Loading Profile</h1>
          <p className="mt-3 text-muted-foreground">Please try again later.</p>
        </main>
        <Footer />
      </div>
    );
  }

  if (isLoading || !profileData) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navbar />
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </main>
        <Footer />
      </div>
    );
  }

  const { user, items, meta } = profileData;
  const totalPages = typeof meta?.pages === "number" && meta.pages > 0 ? meta.pages : 1;

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="flex-1">
        {/* Header / Hero Section */}
        <div className="bg-muted/30 border-b">
          <div className="mx-auto max-w-5xl px-6 py-12 md:py-20">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-8">
              <Avatar
                src={user.avatar_url}
                alt={user.display_name || user.username}
                fallback={(user.display_name?.[0] || user.username[0])?.toUpperCase()}
                className="h-24 w-24 md:h-32 md:w-32 border-4 border-background shadow-xl"
              />

              <div className="flex-1 text-center md:text-left space-y-3">
                <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
                  <h1 className="text-3xl font-serif font-bold tracking-tight">{user.display_name || user.username}</h1>
                  <span className="text-muted-foreground font-mono text-sm px-2 py-1 bg-muted rounded">
                    @{user.username}
                  </span>
                </div>

                {user.bio && (
                  <p className="text-muted-foreground max-w-2xl leading-relaxed whitespace-pre-wrap">{user.bio}</p>
                )}

                <div className="pt-4 flex flex-wrap items-center justify-center md:justify-start gap-6">
                  <div className="text-center md:text-left">
                    <p className="text-2xl font-bold">{user.public_item_count}</p>
                    <p className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
                      Public Items
                    </p>
                  </div>
                  <div className="h-8 w-px bg-border hidden md:block" />
                  <ShareButton title={t("profileTitle", { name: user.display_name || user.username })} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="mx-auto max-w-5xl px-6 py-12 space-y-12">
          {/* Inventory Check Tool */}
          <section className="max-w-2xl mx-auto text-center space-y-4">
            <h2 className="text-xl font-serif font-semibold">{t("checkInventory")}</h2>
            <CheckInventory username={user.username} />
          </section>

          {/* Items Grid */}
          <section className="space-y-6">
            <div className="flex items-center justify-between border-b pb-4">
              <h2 className="text-2xl font-serif font-bold">Collection</h2>
              <p className="text-sm text-muted-foreground">{t("hiddenItemNote")}</p>
            </div>

            {items.length > 0 ? (
              <>
                <CollectionGrid items={items} />
                <PublicProfilePager
                  username={user.username}
                  currentPage={currentPage}
                  totalPages={totalPages}
                  shown={items.length}
                  total={typeof meta?.total === "number" ? meta.total : undefined}
                />
              </>
            ) : (
              <EmptyState
                title="Nothing here yet"
                description="This user hasn't shared any items in their public collection yet."
                icon={Library}
              />
            )}
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
