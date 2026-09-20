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
 * Source-level guard that prevents reintroduction of raw JSON.stringify() +
 * dangerouslySetInnerHTML JSON-LD sinks.
 *
 * All SSR JSON-LD must flow through the shared `JsonLdScript` component or
 * `serializeJsonLdForHtml()` helper to prevent stored XSS via catalog or
 * user-controlled values containing `</script>` or other HTML-sensitive chars.
 */

import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

/**
 * Recursively collects all .tsx/.ts files under a directory, excluding node_modules.
 *
 * @param dir - The directory to scan.
 * @returns Array of absolute file paths.
 */
function collectSourceFiles(dir: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next" || entry.name === "dist") continue;
      results.push(...collectSourceFiles(fullPath));
    } else if (entry.isFile() && /\.(tsx?|jsx?)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) {
      results.push(fullPath);
    }
  }
  return results;
}

/**
 * Checks if a file contains an unsafe JSON-LD sink pattern:
 * `dangerouslySetInnerHTML` combined with `JSON.stringify` in the context
 * of `application/ld+json`.
 *
 * @param content - The file content to check.
 * @returns True if an unsafe JSON-LD sink is detected.
 */
function hasUnsafeJsonLdSink(content: string): boolean {
  // Pattern 1: Inline script with application/ld+json and dangerouslySetInnerHTML + JSON.stringify
  // This catches patterns like:
  //   <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(x) }} />
  const inlineScriptPattern = /<script[^>]*application\/ld\+json[^>]*dangerouslySetInnerHTML[^>]*JSON\.stringify/;
  if (inlineScriptPattern.test(content)) return true;

  // Pattern 2: dangerouslySetInnerHTML with JSON.stringify near application/ld+json
  // (catches multi-line or reordered variants)
  const hasLdJsonScript = /application\/ld\+json/.test(content);
  const hasDangerousStringify = /dangerouslySetInnerHTML[\s\S]{0,200}JSON\.stringify/.test(content);
  if (hasLdJsonScript && hasDangerousStringify) return true;

  // Pattern 3: Reverse order - JSON.stringify before dangerouslySetInnerHTML near ld+json
  const hasReversePattern = /JSON\.stringify[\s\S]{0,200}dangerouslySetInnerHTML/.test(content);
  if (hasLdJsonScript && hasReversePattern) return true;

  return false;
}

const FRONTEND_ROOT = path.resolve(__dirname, "../..");
const SCAN_DIRS = [
  path.join(FRONTEND_ROOT, "app"),
  path.join(FRONTEND_ROOT, "components"),
];

// Files that are allowed to contain the pattern (the safe boundary itself)
const ALLOWED_FILES = new Set([
  "json-ld-script.tsx",
  "json-ld-safety-guard.test.ts",
]);

describe("Source-level guard: no raw JSON-LD sinks", () => {
  it("fails on a synthetic unsafe fixture", () => {
    const unsafeFixture = `
      import React from "react";
      export function BadComponent({ data }: { data: Record<string, unknown> }) {
        return (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
          />
        );
      }
    `;
    expect(hasUnsafeJsonLdSink(unsafeFixture)).toBe(true);
  });

  it("fails on a multi-line unsafe fixture", () => {
    const unsafeFixture = `
      const html = JSON.stringify(jsonLd);
      return <script type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: html }} />;
    `;
    expect(hasUnsafeJsonLdSink(unsafeFixture)).toBe(true);
  });

  it("passes on the safe JsonLdScript component (uses serializeJsonLdForHtml, not raw JSON.stringify)", () => {
    const safeContent = `
      import { serializeJsonLdForHtml } from "@/lib/schema-org";
      export function JsonLdScript({ data }: { data: Record<string, unknown> }) {
        return (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: serializeJsonLdForHtml(data) }}
          />
        );
      }
    `;
    expect(hasUnsafeJsonLdSink(safeContent)).toBe(false);
  });

  it("passes on a file that has JSON.stringify but no JSON-LD context", () => {
    const nonJsonLdContent = `
      export function SomeComponent({ data }: { data: unknown }) {
        return <pre>{JSON.stringify(data, null, 2)}</pre>;
      }
    `;
    expect(hasUnsafeJsonLdSink(nonJsonLdContent)).toBe(false);
  });

  it("scans all frontend app/ and components/ source files and finds no unsafe JSON-LD sinks", () => {
    const allFiles = SCAN_DIRS.flatMap(dir => collectSourceFiles(dir));
    expect(allFiles.length).toBeGreaterThan(0);

    const violations: string[] = [];
    for (const filePath of allFiles) {
      const basename = path.basename(filePath);
      if (ALLOWED_FILES.has(basename)) continue;

      const content = fs.readFileSync(filePath, "utf-8");
      if (hasUnsafeJsonLdSink(content)) {
        violations.push(path.relative(FRONTEND_ROOT, filePath));
      }
    }

    expect(violations).toEqual([]);
  });
});
