import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Silence the "multiple lockfiles" workspace-root warning during dev
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Enable standalone output for the production Docker image (Dockerfile.prod)
  output: "standalone",
};

export default nextConfig;
