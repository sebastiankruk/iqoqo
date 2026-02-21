import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Silence the "multiple lockfiles" workspace-root warning during dev
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Enable standalone output for the production Docker image (Dockerfile.prod)
  output: "standalone",
  // Allow cover images from any HTTPS origin (metadata comes from multiple
  // providers: Google Books, Open Library, etc.). Apply optimization per
  // provider once URLs are stabilised; unoptimized prop is used in the
  // component until then.
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
      {
        protocol: "http",
        hostname: "**",
      },
    ],
  },
};

export default nextConfig;
