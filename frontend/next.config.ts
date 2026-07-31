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

const nextConfig: NextConfig = {
  // Use a custom build directory for E2E testing to avoid process locks with the active dev server
  distDir: process.env.IS_E2E ? ".next-e2e" : undefined,
  // Expose the canonical version to client-side code via lib/version.ts
  env: {
    NEXT_PUBLIC_APP_VERSION: APP_VERSION,
  },
  // Remove the X-Powered-By: Next.js response header
  poweredByHeader: false,
  // Silence the "multiple lockfiles" workspace-root warning during dev
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Enable standalone output for the production Docker image (Dockerfile.prod)
  output: "standalone",

  allowedDevOrigins: ["dev.iqoqo.cc", "*.iqoqo.cc"],

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

    return {
      afterFiles: [
        {
          // Proxy to Flask backend for any API routes not handled locally by Next.js app/api/
          source: "/api/:path*",
          destination: `${backendBase}/api/:path*`,
        },
        {
          // Intercept static asset requests (stored as /static/... in DB)
          // and proxy them to the backend API static serving endpoint.
          source: "/static/:path*",
          destination: `${backendBase}/api/static/:path*`,
        },
        {
          // Proxy OpenObserve RUM & Logs to avoid CORS preflight 401s
          source: "/rum/:path*",
          destination: "http://127.0.0.1:5080/rum/:path*",
        },
        {
          // Proxy OTel Collector traces to avoid CORS origin mismatches
          source: "/v1/traces",
          destination: "http://127.0.0.1:4318/v1/traces",
        },
      ],
    };
  },
  // Allow cover images from a restricted set of HTTPS origins (metadata comes
  // from multiple providers: Google Books, Open Library, etc.). Apply
  // optimization per provider once URLs are stabilised; unoptimized prop is
  // used in the component until then.
  images: {
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
