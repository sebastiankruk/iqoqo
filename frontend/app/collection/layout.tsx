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

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Collection - iqoqo",
  description:
    "Browse and discover physical media, books, board games, vinyl records and collectibles in your library.",
  openGraph: {
    title: "Collection - iqoqo",
    description:
      "Browse and discover physical media, books, board games, vinyl records and collectibles in your library.",
  },
};

/**
 * Server layout for collection pages.
 * Injects baseline CollectionPage JSON-LD during SSR so external agents
 * and search engines receive catalog semantic structure in the initial HTML.
 *
 * @param {object} props - Component props.
 * @param {React.ReactNode} props.children - Child elements.
 * @returns {JSX.Element} Layout with Schema.org JSON-LD.
 */
export default function CollectionLayout({ children }: { children: React.ReactNode }) {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "iqoqo Library Collection",
    description: "Browse and discover physical media, books, board games, vinyl records and collectibles.",
    url: "/collection",
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(collectionJsonLd) }} />
      {children}
    </>
  );
}
