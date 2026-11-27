import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output:
    process.platform === "win32" && process.env.NEXT_FORCE_STANDALONE !== "true"
      ? undefined
      : "standalone",
  reactStrictMode: true,
};

export default nextConfig;
