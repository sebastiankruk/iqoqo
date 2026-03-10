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

const nextConfig: NextConfig = {
  // Remove the X-Powered-By: Next.js response header
  poweredByHeader: false,
  // Silence the "multiple lockfiles" workspace-root warning during dev
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Enable standalone output for the production Docker image (Dockerfile.prod)
  output: "standalone",

  // ADD THIS REWRITES SECTION
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        // Proxy to Flask backend. Adjust the port if your Flask runs on a different one.
        // In production Docker, this might point to a container name like "http://backend:5000/api/:path*"
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : "http://127.0.0.1:5000/api/:path*",
      },
    ];
  },
  // Allow cover images from a restricted set of HTTPS origins (metadata comes
  // from multiple providers: Google Books, Open Library, etc.). Apply
  // optimization per provider once URLs are stabilised; unoptimized prop is
  // used in the component until then.
  images: {
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
        hostname: "covers.openlibrary.org",
      },
    ],
  },
};

export default nextConfig;
