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
import type { FrbrTree, FrbrItem } from "@/lib/api/admin";

/**
 * A key-value pair for dynamic metadata editing.
 */
export interface MetaField {
  key: string;
  value: string;
}

/**
 * Form data for Work (F1) entity editing.
 */
export interface WorkFormData {
  title: string;
  type?: string;
  mechanics?: string[];
  metaFields: MetaField[];
}

/**
 * Form data for Expression (F2) entity editing.
 */
export interface ExpressionFormData {
  content_type?: string;
  language?: string;
  kind?: string;
  metaFields: MetaField[];
}

/**
 * Form data for Manifestation (F3) entity editing.
 */
export interface ManifestationFormData {
  type?: string;
  isbn13?: string;
  upc?: string;
  ean?: string;
  publisher?: string;
  publication_date?: string;
  mechanics?: string[];
  metaFields: MetaField[];
}

/**
 * Form data for Item (F5) entity editing.
 */
export interface ItemFormData {
  status?: string;
  condition?: string;
  metaFields: MetaField[];
}

/**
 * Props shared by entity editors.
 */
export interface EntityEditorProps {
  tree: FrbrTree;
  onSubmit: (data: any) => Promise<void>;
}

/**
 * Props for the ItemEditor component.
 */
export interface ItemEditorProps {
  item: FrbrItem;
  onSubmit: (data: ItemFormData) => Promise<void>;
}

/**
 * Converts a snake_case or camelCase key to Title Case for display.
 *
 * @param key - The key to convert
 * @returns Title cased version of the key
 */
export function formatKeyForDisplay(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Transforms a metadata object into an array of key-value pairs for form editing.
 *
 * @param meta - The source metadata object
 * @returns Array of meta field pairs
 */
export function transformMetaToFields(meta: Record<string, unknown> | null | undefined): MetaField[] {
  if (!meta || typeof meta !== "object") return [];
  return Object.entries(meta).map(([key, value]) => ({
    key,
    value: String(value ?? ""),
  }));
}

/**
 * Transforms an array of key-value pairs back into a metadata object.
 *
 * @param fields - The array of meta field pairs
 * @returns The metadata record
 */
export function transformFieldsToMeta(fields: MetaField[]): Record<string, unknown> {
  return fields.reduce(
    (acc, field) => {
      if (field.key.trim()) {
        acc[field.key.trim()] = field.value;
      }
      return acc;
    },
    {} as Record<string, unknown>
  );
}
