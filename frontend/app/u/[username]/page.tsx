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
import { CollectionGrid } from "@/components/collection/collection-grid";
import { ShareButton } from "@/components/ui/share-button";
import { CheckInventory } from "@/components/public/check-inventory";
import { EmptyState } from "@/components/ui/empty-state";
import { Avatar } from "@/components/ui/avatar";
import { Footer } from "@/components/dashboard/footer";
import { Navbar } from "@/components/dashboard/navbar";

interface PublicProfilePageProps {
  params: Promise<{ username: string }>;
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
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Fetches the public items for a given user.
 * @param username - The public username to fetch items for.
 * @returns The items list.
 */
async function getItems(username: string) {
  try {
    const res = await fetch(resolveApiUrl(`/public/u/${username}/items`, true), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return { data: { items: [] } };
    return res.json();
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
  };
}

/**
 * Public profile page for a user.
 * @param props - Component props.
 * @param props.params - The route parameters.
 * @returns The rendered page.
 */
export default async function PublicProfilePage({ params }: PublicProfilePageProps) {
  const { username } = await params;

  // Guard first: if the profile is not found (private or non-existent), return 404
  // immediately BEFORE calling getTranslations(). This prevents TypeScript from
  // executing subsequent lines (like profileRes.data) on a null profileRes, which
  // would cause a runtime TypeError → HTTP 500 instead of the expected 404.
  const profileRes = await getProfile(username);
  if (!profileRes || !profileRes.success) {
    return notFound();
  }

  const t = await getTranslations("Public");

  const user = profileRes.data;

  const itemsRes = await getItems(username);
  const items = itemsRes.data.items || [];

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
              <CollectionGrid items={items} />
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
