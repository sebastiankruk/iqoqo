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
import { serializeJsonLdForHtml } from "@/lib/schema-org";

export interface JsonLdScriptProps {
  /** The JSON-LD object to embed. Will be serialized through the HTML-safe boundary. */
  data: Record<string, unknown>;
}

/**
 * Renders a `<script type="application/ld+json">` element with HTML-safe serialization.
 *
 * All SSR JSON-LD sinks MUST route through this component (or `serializeJsonLdForHtml`)
 * to prevent stored XSS via catalog or user-controlled values containing `</script>`
 * or other HTML-sensitive characters.
 *
 * @param {JsonLdScriptProps} props - Component properties.
 * @returns {JSX.Element} Script tag with safely serialized JSON-LD.
 */
export function JsonLdScript({ data }: JsonLdScriptProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: serializeJsonLdForHtml(data) }}
    />
  );
}
