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

/**
 * Escape text for safe interpolation into an HTML string.
 *
 * Only for the cases where a value must be spliced into markup that is
 * written as a raw string -- `document.write` into a print window, or a
 * server-rendered template. React escapes automatically, so ordinary JSX
 * interpolation must NOT be passed through this: it would double-encode
 * characters React already handles.
 *
 * `&` is replaced first so an already-escaped entity is not double-decoded by
 * a later substitution.
 *
 * @param value - The untrusted text to encode. Nullish becomes an empty string.
 * @returns The text with `&`, `<`, `>`, `"` and `'` replaced by entities.
 */
export function escapeHtml(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}