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

import React from "react";
import { buildWorkJsonLd, type WorkJsonLdOptions } from "@/lib/schema-org";

export interface WorkStructuredDataProps {
  data: WorkJsonLdOptions;
}

/**
 * Injects Schema.org CreativeWork JSON-LD structured data into the document
 * representing the FRBR Work and its embodied Manifestations.
 *
 * @param {WorkStructuredDataProps} props - Component properties.
 * @returns {JSX.Element} Script tag with application/ld+json.
 */
export function WorkStructuredData({ data }: WorkStructuredDataProps) {
  const jsonLd = buildWorkJsonLd(data);

  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />;
}
