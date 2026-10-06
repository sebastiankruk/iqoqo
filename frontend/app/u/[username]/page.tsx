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

import { notFound } from "next/navigation";
import { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Library } from "lucide-react";

import { resolveApiUrl } from "@/lib/utils";
import { buildProfileJsonLd } from "@/lib/schema-org";
import { JsonLdScript } from "@/components/json-ld-script";
import { CollectionGrid } from "@/components/collection/collection-grid";
import { PublicProfilePager } from "@/components/public/public-profile-pager";
import { ShareButton } from "@/components/ui/share-button";
import { CheckInventory } from "@/components/public/check-inventory";
import { EmptyState } from "@/components/ui/empty-state";
import { Avatar } from "@/components/ui/avatar";
import { Footer } from "@/components/dashboard/footer";
import { Navbar } from "@/components/dashboard/navbar";

/** Items requested per page on the public profile. Matches the API default. */
const ITEMS_PER_PAGE = 24;

interface PublicProfilePageProps {
  params: Promise<{ username: string }>;
  searchParams?: Promise<{ page?: string }>;
}

/**
 * Fetches user profile data for the public page.
 * @param username - The public username to fetch.
 * @returns The user profile data or null if not found.
 */
async function getProfile(username: string) {
  try {
    const res = await fetch(resolveApiUrl(`/public/u/${username}`, true), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetches one page of the public items for a given user.
 *
 * The endpoint is paginated server-side (`page`/`per_page`, capped at 100 by
 * the API), and defaults to 24. Without forwarding the page number a collector
 * with more items than that had no way to reach the rest -- the first 24 were
 * simply all they ever saw.
 *
 * @param username - The public username to fetch items for.
 * @param page - 1-based page number.
 * @returns The items list plus the pagination envelope.
 */
async function getItems(username: string, page = 1) {
  try {
    const qs = `?page=${encodeURIComponent(page)}&per_page=${ITEMS_PER_PAGE}`;
    const res = await fetch(resolveApiUrl(`/public/u/${username}/items${qs}`, true), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return { data: { items: [] } };
    return await res.json();
  } catch {
    return { data: { items: [] } };
  }
}

/**
 * Generates SEO metadata for the public profile page.
 * @param props - Component props.
 * @param props.params - The route parameters.
 * @returns Metadata object for Next.js.
 */
export async function generateMetadata({ params }: PublicProfilePageProps): Promise<Metadata> {
  const { username } = await params;
  const profileRes = await getProfile(username);

  if (!profileRes || !profileRes.success) {
    return { title: "User Not Found - iqoqo" };
  }

  const user = profileRes.data;
  const displayName = user.display_name || user.username;

  return {
    title: `${displayName} (@${user.username}) - iqoqo Collection`,
    description: user.bio || `Browse ${displayName}'s library on iqoqo.`,
    openGraph: {
      title: `${displayName}'s Collection`,
      description: user.bio || `Explore a library of ${user.public_item_count} items.`,
      images: user.avatar_url ? [{ url: user.avatar_url }] : [],
    },
    alternates: {
      types: {
        "application/rss+xml": [
          { url: `/api/public/u/${user.username}/feed.xml`, title: `${displayName}'s Library Feed` },
        ],
        "application/ld+json": [
          { url: `/api/public/u/${user.username}/items?format=json-ld`, title: `${displayName}'s Library JSON-LD` },
        ],
      },
    },
  };
}

/**
 * Public profile page for a user.
 * @param props - Component props.
 * @param props.params - The route parameters.
 * @param props.searchParams - Query string, carrying an optional `page`.
 * @returns The rendered page.
 */
export default async function PublicProfilePage({ params, searchParams }: PublicProfilePageProps) {
  const emptySearch: { page?: string } = {};
  const [{ username }, resolvedSearchParams] = await Promise.all([
    params,
    searchParams ?? Promise.resolve(emptySearch),
  ]);

  // Clamp before use. The value comes straight off the query string, so an
  // arbitrary string ("abc", "-3") must not reach the API or the pager. A
  // non-numeric or out-of-range page falls back to the first page.
  const rawPage = Number.parseInt(resolvedSearchParams?.page ?? "1", 10);
  const currentPage = Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1;

  // The profile guard has to resolve before anything reads profileRes.data, but
  // the items fetch and the translations do not depend on it -- only on
  // `username`, which is already known. Running them concurrently removes a
  // serial round trip from every public profile render. The 404 check below
  // still gates rendering, so the early fetch is wasted only when the profile
  // does not exist.
  const itemsPromise = getItems(username, currentPage);
  const translationsPromise = getTranslations("Public");

  // Guard: if the profile is not found (private or non-existent), return 404
  // immediately BEFORE reading profileRes.data. Accessing it on a null
  // profileRes would cause a runtime TypeError → HTTP 500 instead of 404.
  const profileRes = await getProfile(username);
  if (!profileRes || !profileRes.success) {
    return notFound();
  }

  const t = await translationsPromise;

  const user = profileRes.data;

  const itemsRes = await itemsPromise;
  const items = itemsRes.data.items || [];
  const meta = itemsRes.meta ?? {};
  const totalPages = typeof meta.pages === "number" && meta.pages > 0 ? meta.pages : 1;

  const profileJsonLd = buildProfileJsonLd({
    username: user.username,
    displayName: user.display_name,
    bio: user.bio,
    avatarUrl: user.avatar_url,
    // The API's own count, not this page's slice length: a profile with 500
    // public items reports 24 here, which would publish a wrong count to
    // search engines via the JSON-LD.
    publicItemCount: user.public_item_count ?? items.length,
  });

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <JsonLdScript data={profileJsonLd} />
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
                  username={username}
                  currentPage={currentPage}
                  totalPages={totalPages}
                  shown={items.length}
                  total={typeof meta.total === "number" ? meta.total : undefined}
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
