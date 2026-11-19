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

import { notFound } from "next/navigation";
import { cookies } from "next/headers";

import { buildPaginationWindow } from "@/lib/pagination";
import { resolveApiUrl } from "@/lib/utils";
import { Footer } from "@/components/dashboard/footer";
import { NavbarWithSuspense as Navbar } from "@/components/dashboard/navbar-wrapper";

export interface SharedCollectionItem {
  id: number | string;
  manifestation_id?: number | string;
  title: string;
  authors?: string[];
  cover_url?: string;
  status?: string;
  collection_status?: string;
  content_type?: string | null;
  format?: string | null;
  ean?: string | null;
  upc?: string | null;
  publisher?: string | null;
  publication_year?: string | number | null;
  catalog_number?: string | null;
  country?: string | null;
  lod_links?: Record<string, string> | null;
}

export interface SharedCollectionData {
  author: string;
  collection_name: string;
  collection_description?: string;
  total?: number;
  page?: number;
  per_page?: number;
  pages?: number;
  items: SharedCollectionItem[];
}

export interface SharedCollectionResponse {
  success: boolean;
  data: SharedCollectionData;
}

export type SharedCollectionResult =
  { kind: "success"; response: SharedCollectionResponse } | { kind: "not-found" } | { kind: "error" };

export const AI_JSONLD_PER_PAGE = 60;
export const SHARE_UI_PER_PAGE = 48;

/** Resolves the public origin for absolute links in SSR HTML and JSON-LD pagination. */
export function resolvePublicOrigin(): string {
  for (const raw of [process.env.NEXT_PUBLIC_FRONTEND_URL, process.env.BASE_URL]) {
    const trimmed = raw?.trim();
    if (trimmed && (trimmed.startsWith("http://") || trimmed.startsWith("https://"))) {
      return trimmed.replace(/\/+$/, "");
    }
  }
  return "https://iqoqo.cc";
}

/**
 * Safely retrieve request cookies when running inside a dynamic SSR request.
 * Returns empty headers during Capacitor static builds or unit tests.
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
    // RequestAsyncStorage is unavailable outside active requests
  }
  return {};
}

/**
 * Fetches a paginated shared collection by its secure token.
 *
 * Forwards caller cookies so authenticated friends receive Friend Bonus items
 * on SSR while anonymous requests keep 60-second ISR caching.
 *
 * @param token - The unique share token.
 * @param page - 1-based page number.
 * @param perPage - Items per page.
 * @returns The shared collection data, a not-found result, or a server error result.
 */
export async function getSharedCollection(
  token: string,
  page = 1,
  perPage = SHARE_UI_PER_PAGE
): Promise<SharedCollectionResult> {
  try {
    const cookieHeaders = await getCookieHeader();
    const hasCookies = Boolean(cookieHeaders.Cookie);
    const res = await fetch(
      resolveApiUrl(`/public/share/${token}?page=${page}&per_page=${perPage}`, true),
      hasCookies ? { headers: cookieHeaders, cache: "no-store" } : { next: { revalidate: 60 } }
    );
    if (res.status === 404) return { kind: "not-found" };
    if (!res.ok) return { kind: "error" };

    const response = (await res.json()) as SharedCollectionResponse;
    if (!response.success || !response.data) return { kind: "error" };
    return { kind: "success", response };
  } catch {
    return { kind: "error" };
  }
}

/**
 * Renders the standard server error shell for shared collection SSR routes.
 */
export function renderSharedCollectionError() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-16">
        <section role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
          <h1 className="text-2xl font-serif font-bold">Server Error</h1>
          <p className="mt-3 text-muted-foreground">Please Try Again Later</p>
        </section>
      </main>
      <Footer />
    </div>
  );
}

/**
 * Renders the chromeless HTML-wrapped minified JSON-LD view for a paginated
 * slice of a shared collection using clean, query-free `/share/<token>/jsonld/<page>` links.
 *
 * @param token - The unique share token.
 * @param requestedPage - 1-based page number to serialize.
 */
export async function renderSharedCollectionJsonLdView(token: string, requestedPage: number) {
  const collectionRes = await getSharedCollection(token, requestedPage, AI_JSONLD_PER_PAGE);
  if (collectionRes.kind === "not-found") {
    notFound();
  }
  if (collectionRes.kind === "error") {
    return renderSharedCollectionError();
  }

  const collection = collectionRes.response.data;
  const items = collection.items || [];
  const totalItems = collection.total ?? items.length;
  const currentPage = collection.page ?? requestedPage;
  const totalPages = collection.pages ?? (totalItems > 0 ? Math.ceil(totalItems / AI_JSONLD_PER_PAGE) : 0);
  const publicBaseUrl = resolvePublicOrigin();

  const windowPages = buildPaginationWindow(currentPage, totalPages);
  const pageUrl = (p: number) => `${publicBaseUrl}/share/${token}/jsonld/${p}`;
  const compactPayload = {
    "@context": {
      "@vocab": "https://schema.org/",
      t: "name",
      a: "byArtist",
      f: "musicReleaseFormat",
      l: "recordLabel",
      c: "catalogNumber",
      y: "datePublished",
      g: "gtin13",
    },
    "@type": "CollectionPage",
    name: collection.collection_name,
    author: collection.author,
    totalItems,
    page: currentPage,
    perPage: AI_JSONLD_PER_PAGE,
    totalPages,
    ...(currentPage < totalPages ? { nextPage: pageUrl(currentPage + 1) } : {}),
    pages: windowPages.map(pageUrl),
    itemListElement: items.map((item: SharedCollectionItem) => ({
      t: item.title,
      ...(item.authors && item.authors.length > 0 ? { a: item.authors.join(", ") } : {}),
      ...(item.format || item.content_type ? { f: item.format || item.content_type } : {}),
      ...(item.publisher ? { l: item.publisher } : {}),
      ...(item.catalog_number ? { c: item.catalog_number } : {}),
      ...(item.publication_year !== null && item.publication_year !== undefined && item.publication_year !== ""
        ? { y: String(item.publication_year) }
        : {}),
      ...(item.ean || item.upc ? { g: String(item.ean || item.upc) } : {}),
    })),
  };

  return (
    <main className="mx-auto max-w-4xl p-4 font-mono text-xs">
      {windowPages.length > 0 && (
        <nav aria-label="JSON-LD Pages" className="mb-3 flex flex-wrap gap-2">
          {windowPages.map(p => (
            <a key={p} href={pageUrl(p)} aria-current={p === currentPage ? "page" : undefined}>
              Page {p}
            </a>
          ))}
          {currentPage < totalPages && <a href={pageUrl(currentPage + 1)}>Next Page</a>}
        </nav>
      )}
      <pre id="jsonld-payload" className="whitespace-pre-wrap break-all">
        {JSON.stringify(compactPayload)}
      </pre>
    </main>
  );
}
