import fs from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

/**
 * Load environment variables pulled by `neon deploy` from the repository root `.env.local` / `.env`
 * so Next.js build and server runtime always receive all Neon service variables without file duplication.
 */
function loadRootNeonEnv(): void {
  const candidates = [
    path.resolve(__dirname, "../../.env.local"),
    path.resolve(__dirname, "../../.env"),
    path.resolve(__dirname, "../.env.local"),
    path.resolve(__dirname, "../.env"),
  ];
  for (const filePath of candidates) {
    if (!fs.existsSync(filePath)) continue;
    try {
      const content = fs.readFileSync(filePath, "utf8");
      for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith("#")) continue;
        const eqIdx = line.indexOf("=");
        if (eqIdx <= 0) continue;
        const key = line.slice(0, eqIdx).trim();
        let val = line.slice(eqIdx + 1).trim();
        if (
          (val.startsWith('"') && val.endsWith('"')) ||
          (val.startsWith("'") && val.endsWith("'"))
        ) {
          val = val.slice(1, -1);
        }
        if (process.env[key] === undefined) {
          process.env[key] = val;
        }
      }
    } catch {
      // Ignore env read errors
    }
  }
}

loadRootNeonEnv();

const nextConfig: NextConfig = {
  output:
    process.platform === "win32" && process.env.NEXT_FORCE_STANDALONE !== "true"
      ? undefined
      : "standalone",
  reactStrictMode: true,
  cleanDistDir: false,
  serverExternalPackages: ["@neon/env", "@neon/config"],
};

export default nextConfig;
