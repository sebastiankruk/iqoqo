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
 * Fields that should always be stored as arrays in metadata.
 * These fields accept comma-separated input and are automatically split.
 */
export const ARRAY_META_FIELDS = new Set([
  "authors",
  "translators",
  "illustrators",
  "editors",
  "contributors",
  "tags",
  "genres",
  "mechanics",
  "narrators",
  "publishers",
]);

/**
 * Normalizes a value to an array for known array fields.
 * Handles comma/semicolon-separated strings, existing arrays, and empty values.
 *
 * @param key - The metadata field key
 * @param value - The raw value from form input
 * @returns Normalized value (array for known fields, original value otherwise)
 */
export function normalizeMetaValue(key: string, value: string): string | string[] {
  if (!ARRAY_META_FIELDS.has(key)) {
    return value;
  }
  if (!value || typeof value !== "string") {
    return [];
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return [];
  }
  return trimmed
    .split(/[,;]/)
    .map(part => part.trim())
    .filter(part => part.length > 0);
}

/**
 * Ensures a value is always an array.
 * Converts strings to single-element arrays, handles null/undefined.
 *
 * @param value - The value to normalize
 * @returns Always an array
 */
export function ensureArray(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  if (typeof value === "string") {
    return value
      .split(/[,;]/)
      .map(part => part.trim())
      .filter(part => part.length > 0);
  }
  return [];
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
 * Converts array values to comma-separated strings for display in text inputs.
 *
 * @param meta - The source metadata object
 * @returns Array of meta field pairs with array values joined as strings
 */
export function transformMetaToFields(meta: Record<string, unknown> | null | undefined): MetaField[] {
  if (!meta || typeof meta !== "object") return [];
  return Object.entries(meta).map(([key, value]) => {
    const displayValue = Array.isArray(value)
      ? value.join(", ")
      : String(value ?? "");
    return { key, value: displayValue };
  });
}

/**
 * Transforms an array of key-value pairs back into a metadata object.
 * Automatically normalizes known array fields (authors, tags, etc.)
 * by splitting comma-separated values into arrays.
 *
 * @param fields - The array of meta field pairs
 * @returns The metadata record with normalized array values
 */
export function transformFieldsToMeta(fields: MetaField[]): Record<string, unknown> {
  return fields.reduce(
    (acc, field) => {
      const key = field.key.trim();
      if (key) {
        acc[key] = normalizeMetaValue(key, field.value);
      }
      return acc;
    },
    {} as Record<string, unknown>
  );
}
