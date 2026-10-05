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

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Security headers on the token-bearing frontend routes.
 *
 * These protections used to live on a server-rendered Flask page. Now that the
 * screens are frontend routes, `next.config.ts` owns them -- and a header rule in
 * a config file is exactly the kind of thing that gets dropped in a refactor
 * without anything failing. The project rule "Flask Is API-Only" therefore has to
 * be enforced from both ends: this asserts the frontend keeps what Flask gave up.
 */
const configPath = join(process.cwd(), "next.config.ts");

/**
 * Read the headers block for `/account/:path*` out of the config source.
 *
 * Parsed textually rather than by importing the config, because importing it
 * pulls in the Next.js plugin and the whole build config into a unit test.
 *
 * @returns The raw text of the matching headers rule
 */
function accountHeadersRule(): string {
  const source = readFileSync(configPath, "utf-8");
  const start = source.indexOf('source: "/account/:path*"');
  expect(start, "next.config.ts must declare headers for /account/:path*").toBeGreaterThan(-1);
  const end = source.indexOf("]", start);
  return source.slice(start, end === -1 ? undefined : end);
}

describe("token-bearing route headers", () => {
  it("sets no-referrer so the token in the URL cannot leak onward", () => {
    // The actual control against referrer leakage -- not the absence of
    // subresources, which the frontend has plenty of.
    expect(accountHeadersRule()).toContain('key: "Referrer-Policy", value: "no-referrer"');
  });

  it("refuses framing", () => {
    // Being framed turns "confirm" into "confirm what the frame's owner says",
    // on a page whose whole purpose is a single irreversible button.
    expect(accountHeadersRule()).toContain('key: "X-Frame-Options", value: "DENY"');
  });

  it("is not cached", () => {
    // A shared machine, a proxy cache, or the back button must not be able to
    // replay a page that was rendered while a token was live.
    expect(accountHeadersRule()).toMatch(/key: "Cache-Control", value: "[^"]*no-store/);
  });

  it("is not indexed and does not sniff", () => {
    expect(accountHeadersRule()).toContain('key: "X-Robots-Tag"');
    expect(accountHeadersRule()).toContain('key: "X-Content-Type-Options", value: "nosniff"');
  });
});
