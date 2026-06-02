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
import type { NextConfig } from "next";
import path from "path";
import { createRequire } from "module";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

// Read version from package.json so NEXT_PUBLIC_APP_VERSION is always in sync
// with the canonical semver set by `make bump-version` / `scripts/sync_version.py`.
const require = createRequire(import.meta.url);
const { version: APP_VERSION } = require("./package.json") as { version: string };

// When CAPACITOR_BUILD=true, emit a fully static export for Capacitor instead
// of the default standalone server output used by the production Docker image.
const isCapacitorBuild = process.env.CAPACITOR_BUILD === "true";

const nextConfig: NextConfig = {
  // Expose the canonical version to client-side code via lib/version.ts
  // NEXT_PUBLIC_IS_CAPACITOR is used in app/api/auth-exchange/route.ts to set
  // `export const dynamic = "force-static"` so that `output: "export"` succeeds
  // without making the route permanently static in web/standalone builds.
  env: {
    NEXT_PUBLIC_APP_VERSION: APP_VERSION,
    NEXT_PUBLIC_IS_CAPACITOR: isCapacitorBuild ? "true" : "false",
  },
  // Remove the X-Powered-By: Next.js response header
  poweredByHeader: false,
  // Silence the "multiple lockfiles" workspace-root warning during dev
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Standalone for Docker; static export for Capacitor native builds
  output: isCapacitorBuild ? "export" : "standalone",
  allowedDevOrigins: ["dev.iqoqo.cc", "*.iqoqo.cc"],
  skipTrailingSlashRedirect: true,

  /**
   * Rewrites for API and other requests.
   *
   * @returns {Promise<Array<{ source: string, destination: string }>>} The rewrites
   */
  async rewrites() {
    // NEXT_PUBLIC_API_URL may carry a trailing "/api" suffix (legacy .env format) or be relative "/api".
    // We favor FLASK_API_URL if available for the server-side proxy destination.
    const apiUrl = process.env.FLASK_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5000/api";
    const backendBase = apiUrl.replace(/\/api\/?$/, "");

    return [
      {
        // Only proxy to Flask if NOT an internal Next.js auth exception route.
        // aligning with deploy/nginx.conf locations
        source: "/api/:path((?!auth-exchange|auth/logout).*)",
        // Proxy to Flask backend. All browser API calls go through Next.js
        // (same-origin) so the session cookie is forwarded without CORS issues.
        destination: `${backendBase}/api/:path`,
      },
      {
        // Intercept static asset requests (stored as /static/... in DB)
        // and proxy them to the backend API static serving endpoint.
        source: "/static/:path*",
        destination: `${backendBase}/api/static/:path*`,
      },
    ];
  },
  // Allow cover images from a restricted set of HTTPS origins (metadata comes
  // from multiple providers: Google Books, Open Library, etc.). Apply
  // optimization per provider once URLs are stabilised; unoptimized prop is
  // used in the component until then.
  // In Capacitor builds there is no server-side optimiser, so disable it.
  images: isCapacitorBuild
    ? { unoptimized: true }
    : {
        localPatterns: [
          {
            pathname: "/api/static/**",
          },
          {
            pathname: "/static/**",
          },
          {
            pathname: "/*.png",
          },
          {
            pathname: "/*.svg",
          },
        ],
        remotePatterns: [
          {
            protocol: "https",
            hostname: "books.google.com",
          },
          {
            protocol: "https",
            hostname: "books.googleusercontent.com",
          },
          {
            protocol: "https",
            hostname: "lh3.googleusercontent.com",
          },
          {
            protocol: "https",
            hostname: "covers.openlibrary.org",
          },
          {
            protocol: "https",
            hostname: "i.discogs.com",
          },
          {
            protocol: "https",
            hostname: "coverartarchive.org",
          },
          {
            protocol: "https",
            hostname: "img.discogs.com",
          },
          {
            protocol: "https",
            hostname: "archive.org",
          },
          {
            protocol: "https",
            hostname: "images.sk-static.com",
          },
        ],
      },
};

export default withNextIntl(nextConfig);
