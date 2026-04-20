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
 * Application version exported as a typed constant.
 *
 * The value is injected at build time by Next.js via the `NEXT_PUBLIC_APP_VERSION`
 * environment variable, which `next.config.ts` derives from `package.json` so that
 * `pyproject.toml` remains the single source of truth for the semver string.
 *
 * Falls back to `"dev"` in local development when the env variable is absent.
 *
 * Usage:
 * ```ts
 * import { APP_VERSION } from "@/lib/version";
 * console.log(APP_VERSION); // e.g. "0.4.1"
 * ```
 */
export const APP_VERSION: string = process.env.NEXT_PUBLIC_APP_VERSION ?? "dev";
