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
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//

import { toast } from "sonner";

export type ExportFormat = "json-ld" | "turtle" | "json";

export interface ExportFormatOption {
  value: ExportFormat;
  label: string;
  description: string;
  extension: string;
}

export const EXPORT_FORMAT_OPTIONS: ExportFormatOption[] = [
  {
    value: "json-ld",
    label: "JSON-LD (Canonical Linked Data)",
    description: "W3C standard JSON format with FRBR & Schema.org semantic context.",
    extension: "jsonld",
  },
  {
    value: "turtle",
    label: "RDF Turtle (.ttl)",
    description: "Concise human-readable RDF graph preserving full ontology triples.",
    extension: "ttl",
  },
  {
    value: "json",
    label: "Hierarchical JSON",
    description: "Standard nested JSON array preserving the Work -> Expression -> Manifestation -> Item hierarchy.",
    extension: "json",
  },
];

/**
 * Downloads the user's personal collection in the specified format.
 * Handles authenticated streaming fetch, parses Content-Disposition header
 * for filename, creates a download blob, and displays toast notifications.
 *
 * @param format - Export format ('json-ld' | 'turtle' | 'json')
 * @returns {Promise<void>} A promise that resolves when download triggers
 */
export async function downloadCollectionExport(format: ExportFormat = "json-ld"): Promise<void> {
  const ext = format === "json-ld" ? "jsonld" : format === "turtle" ? "ttl" : "json";
  let fallbackFilename = `iqoqo-export.${ext}`;

  try {
    const response = await fetch(`/api/v1/items/export?format=${encodeURIComponent(format)}`, {
      method: "GET",
      headers: {
        Accept: format === "json-ld" ? "application/ld+json" : format === "turtle" ? "text/turtle" : "application/json",
      },
      credentials: "same-origin",
    });

    if (!response.ok) {
      let errorMessage = `Export failed with HTTP ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson?.error) {
          errorMessage = errJson.error;
        }
      } catch {
        // use default error message
      }
      toast.error(errorMessage);
      throw new Error(errorMessage);
    }

    const disposition = response.headers.get("Content-Disposition");
    if (disposition) {
      const filenameMatch = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (filenameMatch && filenameMatch[1]) {
        fallbackFilename = filenameMatch[1].replace(/['"]/g, "").trim();
      }
    }

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = fallbackFilename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);

    toast.success(`Export downloaded: ${fallbackFilename}`);
  } catch (error) {
    if (error instanceof Error && error.message) {
      // Toast already shown for API errors
    } else {
      toast.error("Failed to export collection");
    }
    throw error;
  }
}
