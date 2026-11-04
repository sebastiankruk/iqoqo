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
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import { Library } from "lucide-react";

import { resolveApiUrl } from "@/lib/utils";
import { buildProfileJsonLd } from "@/lib/schema-org";
import { JsonLdScript } from "@/components/json-ld-script";
import { PublicProfileClient } from "@/components/public/public-profile-client";
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";

/** Items requested per page on the public profile. Matches the API default. */
const ITEMS_PER_PAGE = 24;

interface PublicProfilePageProps {
  params: Promise<{ username: string }>;
  searchParams?: Promise<{ page?: string }>;
}

/** Generates static placeholder params for Capacitor static export builds. */
export function generateStaticParams() {
  return [{ username: "_placeholder" }];
}

/**
 * Safely retrieve request cookies if within an active request context.
 * Returns empty headers in unit test or static environments.
 */
async function getCookieHeader(): Promise<Record<string, string>> {
  if (process.env.CAPACITOR_BUILD === "true") {
    return {};
  }
  try {
    const cookieStore = await cookies();
    const cookieHeader = cookieStore?.toString();
    if (cookieHeader) {
      return { Cookie: cookieHeader };
    }
  } catch {
    // RequestAsyncStorage not available outside active request
  }
  return {};
}

/**
 * Fetches user profile data for the public page.
 * @param username - The public username to fetch.
 * @returns The user profile data or null if not found.
 */
async function getProfile(username: string) {
  try {
    const headers = await getCookieHeader();
    const res = await fetch(resolveApiUrl(`/public/u/${username}`, true), {
      headers,
      cache: "no-store",
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
    const headers = await getCookieHeader();
    const qs = `?page=${encodeURIComponent(page)}&per_page=${ITEMS_PER_PAGE}`;
    const res = await fetch(resolveApiUrl(`/public/u/${username}/items${qs}`, true), {
      headers,
      cache: "no-store",
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
  if (username === "_placeholder") {
    return { title: "iqoqo" };
  }
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
  const { username } = await params;

  if (username === "_placeholder") {
    return <PublicProfileClient initialData={null} initialUsername="_placeholder" />;
  }

  const isStaticExport = process.env.CAPACITOR_BUILD === "true";
  const resolvedSearchParams = isStaticExport ? {} : ((await searchParams) ?? {});

  const rawPage = Number.parseInt(resolvedSearchParams?.page ?? "1", 10);
  const currentPage = Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1;

  const itemsPromise = getItems(username, currentPage);

  const profileRes = await getProfile(username);
  if (!profileRes || !profileRes.success) {
    return notFound();
  }

  const user = profileRes.data;

  const itemsRes = await itemsPromise;
  const items = itemsRes.data?.items || [];
  const meta = itemsRes.meta ?? {};

  const profileJsonLd = buildProfileJsonLd({
    username: user.username,
    displayName: user.display_name,
    bio: user.bio,
    avatarUrl: user.avatar_url,
    publicItemCount: user.public_item_count ?? items.length,
  });

  return (
    <>
      <JsonLdScript data={profileJsonLd} />
      <PublicProfileClient
        initialData={{
          user,
          items,
          meta,
          currentPage,
        }}
        initialUsername={username}
      />
    </>
  );
}
