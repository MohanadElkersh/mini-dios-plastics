/**
 * Neon Cloud Platform Server SDK Wiring for Next.js App Router (`@neon/env`, `@neondatabase/serverless`, `@neon/realtime`).
 *
 * Uses the environment variables pulled by `neon deploy`:
 * - `DATABASE_URL`, `DATABASE_URL_UNPOOLED` (Postgres via `@neondatabase/serverless`)
 * - `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL` (Neon Auth)
 * - `NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN` (Neon AI Gateway)
 * - `NEON_BRANCH`, `NEON_BRANCH_ID`, `NEON_FUNCTION_HOST_SUFFIX` (Neon Functions via `functionBaseUrl`)
 * - `NEON_REALTIME_URL`, `NEON_REALTIME_SECRET` (Neon Realtime via `createRealtime` + `rawSql`)
 */
import { functionBaseUrl, parseEnv } from "@neon/env";
import { createRealtime, rawSql, type SealedLiveQuery } from "@neon/realtime/server";
import { neon } from "@neondatabase/serverless";

const NEON_POLICY_CONFIG = {
  preview: {
    realtime: true,
  },
  auth: true,
  aiGateway: true,
  functions: {
    hello: { name: "Hello World", source: "./hello.ts" },
  },
} as const;

export interface ProvisionedNeonEnv {
  DATABASE_URL?: string;
  DATABASE_URL_UNPOOLED?: string;
  NEON_BRANCH?: string;
  NEON_BRANCH_ID?: string;
  NEON_AUTH_BASE_URL?: string;
  NEON_AUTH_JWKS_URL?: string;
  NEON_FUNCTION_HOST_SUFFIX?: string;
  NEON_AI_GATEWAY_TOKEN?: string;
  NEON_AI_GATEWAY_BASE_URL?: string;
  NEON_REALTIME_URL?: string;
  NEON_REALTIME_SECRET?: string;
}

export function getNeonEnv(): ProvisionedNeonEnv {
  try {
    const parsed = parseEnv(NEON_POLICY_CONFIG);
    return {
      DATABASE_URL: parsed.postgres.databaseUrl,
      DATABASE_URL_UNPOOLED: parsed.postgres.databaseUrlUnpooled,
      NEON_BRANCH: parsed.branch?.name ?? process.env.NEON_BRANCH,
      NEON_BRANCH_ID: parsed.branch?.id ?? process.env.NEON_BRANCH_ID,
      NEON_FUNCTION_HOST_SUFFIX:
        parsed.branch?.functionHostSuffix ?? process.env.NEON_FUNCTION_HOST_SUFFIX,
      NEON_AUTH_BASE_URL: parsed.auth.baseUrl,
      NEON_AUTH_JWKS_URL: parsed.auth.jwksUrl,
      NEON_AI_GATEWAY_TOKEN: parsed.aiGateway.apiKey,
      NEON_AI_GATEWAY_BASE_URL: parsed.aiGateway.baseUrl,
      NEON_REALTIME_URL: parsed.realtime.url,
      NEON_REALTIME_SECRET: parsed.realtime.secret,
    };
  } catch {
    return {
      DATABASE_URL: process.env.DATABASE_URL,
      DATABASE_URL_UNPOOLED: process.env.DATABASE_URL_UNPOOLED,
      NEON_BRANCH: process.env.NEON_BRANCH,
      NEON_BRANCH_ID: process.env.NEON_BRANCH_ID,
      NEON_AUTH_BASE_URL: process.env.NEON_AUTH_BASE_URL,
      NEON_AUTH_JWKS_URL: process.env.NEON_AUTH_JWKS_URL,
      NEON_FUNCTION_HOST_SUFFIX: process.env.NEON_FUNCTION_HOST_SUFFIX,
      NEON_AI_GATEWAY_TOKEN: process.env.NEON_AI_GATEWAY_TOKEN,
      NEON_AI_GATEWAY_BASE_URL: process.env.NEON_AI_GATEWAY_BASE_URL,
      NEON_REALTIME_URL: process.env.NEON_REALTIME_URL,
      NEON_REALTIME_SECRET: process.env.NEON_REALTIME_SECRET,
    };
  }
}

/**
 * Derive the Postgres database name from `DATABASE_URL` so `createRealtime` and `DATABASE_URL`
 * can never drift out of sync (as recommended by `@neon/env`).
 */
export function deriveDatabaseFromUrl(databaseUrl?: string): string {
  const raw = databaseUrl || getNeonEnv().DATABASE_URL || "";
  if (!raw) return "neondb";
  try {
    const parsed = new URL(raw);
    return parsed.pathname.replace(/^\//, "") || "neondb";
  } catch {
    return "neondb";
  }
}

/**
 * Create a low-latency HTTP SQL query function via `@neondatabase/serverless`.
 */
export function getNeonSql() {
  const dbUrl = getNeonEnv().DATABASE_URL;
  if (!dbUrl) {
    throw new Error("DATABASE_URL is not configured.");
  }
  return neon(dbUrl);
}

/**
 * Resolve a deployed Neon Function URL using `@neon/env`'s `functionBaseUrl(slug)`.
 */
export function resolveNeonFunctionUrl(slug: string = "hello"): string | null {
  try {
    return functionBaseUrl(slug);
  } catch {
    return null;
  }
}

/**
 * Seal a parameterized live query for Neon Realtime (`@neon/realtime/server`) with zero network round-trips.
 */
export async function sealCheckpointsLiveQuery(
  sandboxId: string = "local",
  limit: number = 25
): Promise<{
  database: string;
  realtimeUrl: string;
  sealedQuery: SealedLiveQuery<Record<string, unknown>>;
}> {
  const env = getNeonEnv();
  const secret = env.NEON_REALTIME_SECRET;
  const realtimeUrl = env.NEON_REALTIME_URL;
  if (!secret || !realtimeUrl) {
    throw new Error("NEON_REALTIME_SECRET or NEON_REALTIME_URL is not configured.");
  }
  const database = deriveDatabaseFromUrl(env.DATABASE_URL);
  const realtime = createRealtime({
    secret,
    db: database,
  });
  const sealedQuery = await realtime.seal({
    query: rawSql<Record<string, unknown>>(
      "SELECT id, sandbox_id, access_code, created_at, trigger_source, title_en, title_ar, risk_score, weekly_savings, otif_pct, currency FROM decision_checkpoints WHERE sandbox_id = $1 ORDER BY created_at DESC LIMIT $2",
      [sandboxId, limit]
    ),
  });
  return {
    database,
    realtimeUrl,
    sealedQuery,
  };
}
