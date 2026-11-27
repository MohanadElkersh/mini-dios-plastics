import { NextResponse } from "next/server";
import {
  deriveDatabaseFromUrl,
  getNeonEnv,
  getNeonSql,
  resolveNeonFunctionUrl,
  sealCheckpointsLiveQuery,
} from "@/lib/neon";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const envSnapshot = getNeonEnv();

  // 1. Neon Postgres via @neondatabase/serverless
  let postgresStatus: Record<string, unknown> = { configured: Boolean(envSnapshot.DATABASE_URL), ok: false };
  try {
    const sql = getNeonSql();
    const rows = await sql`
      SELECT
        current_database() AS db_name,
        current_user AS db_user,
        (SELECT COUNT(*)::int FROM saved_workspaces) AS saved_workspaces_count,
        (SELECT COUNT(*)::int FROM decision_checkpoints) AS decision_checkpoints_count
    `;
    const row = rows[0] || {};
    postgresStatus = {
      configured: true,
      ok: true,
      driver: "@neondatabase/serverless",
      database_name: row.db_name,
      current_user: row.db_user,
      unpooled_configured: Boolean(envSnapshot.DATABASE_URL_UNPOOLED),
      saved_workspaces_count: row.saved_workspaces_count,
      decision_checkpoints_count: row.decision_checkpoints_count,
    };
  } catch (err) {
    postgresStatus = {
      configured: Boolean(envSnapshot.DATABASE_URL),
      ok: false,
      driver: "@neondatabase/serverless",
      error: err instanceof Error ? err.message : String(err),
    };
  }

  // 2. Neon Auth via NEON_AUTH_BASE_URL & NEON_AUTH_JWKS_URL
  let authStatus: Record<string, unknown> = {
    configured: Boolean(envSnapshot.NEON_AUTH_BASE_URL && envSnapshot.NEON_AUTH_JWKS_URL),
    ok: false,
  };
  if (envSnapshot.NEON_AUTH_JWKS_URL) {
    try {
      const resp = await fetch(envSnapshot.NEON_AUTH_JWKS_URL, { cache: "no-store" });
      const data = resp.ok ? ((await resp.json()) as { keys?: Array<{ kid?: string }> }) : {};
      const keys = Array.isArray(data.keys) ? data.keys : [];
      authStatus = {
        configured: true,
        ok: resp.ok && keys.length > 0,
        base_url: envSnapshot.NEON_AUTH_BASE_URL,
        jwks_url: envSnapshot.NEON_AUTH_JWKS_URL,
        status_code: resp.status,
        keys_count: keys.length,
        key_ids: keys.map((k) => k.kid).filter(Boolean),
      };
    } catch (err) {
      authStatus = {
        configured: true,
        ok: false,
        base_url: envSnapshot.NEON_AUTH_BASE_URL,
        jwks_url: envSnapshot.NEON_AUTH_JWKS_URL,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  // 3. Neon Functions via @neon/env functionBaseUrl("hello")
  let functionsStatus: Record<string, unknown> = {
    configured: Boolean(envSnapshot.NEON_BRANCH_ID && envSnapshot.NEON_FUNCTION_HOST_SUFFIX),
    ok: false,
  };
  const helloUrl = resolveNeonFunctionUrl("hello");
  if (helloUrl) {
    try {
      const resp = await fetch(helloUrl, { cache: "no-store" });
      const text = await resp.text();
      functionsStatus = {
        configured: true,
        ok: resp.ok,
        slug: "hello",
        url: helloUrl,
        status_code: resp.status,
        body: text,
      };
    } catch (err) {
      functionsStatus = {
        configured: true,
        ok: false,
        slug: "hello",
        url: helloUrl,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  // 4. Neon Realtime via @neon/realtime/server createRealtime + rawSql
  let realtimeStatus: Record<string, unknown> = {
    configured: Boolean(envSnapshot.NEON_REALTIME_URL && envSnapshot.NEON_REALTIME_SECRET),
    ok: false,
  };
  try {
    const sealed = await sealCheckpointsLiveQuery("local", 10);
    realtimeStatus = {
      configured: true,
      ok: Boolean(sealed.sealedQuery && sealed.realtimeUrl),
      database: sealed.database,
      realtime_url: sealed.realtimeUrl,
      sealed_capability_length: String(sealed.sealedQuery.capability).length,
      query_fingerprint: sealed.sealedQuery.queryFingerprint,
    };
  } catch (err) {
    realtimeStatus = {
      configured: Boolean(envSnapshot.NEON_REALTIME_URL && envSnapshot.NEON_REALTIME_SECRET),
      ok: false,
      database: deriveDatabaseFromUrl(envSnapshot.DATABASE_URL),
      error: err instanceof Error ? err.message : String(err),
    };
  }

  // 5. Neon AI Gateway via NEON_AI_GATEWAY_BASE_URL & NEON_AI_GATEWAY_TOKEN
  let aiGatewayStatus: Record<string, unknown> = {
    configured: Boolean(envSnapshot.NEON_AI_GATEWAY_BASE_URL && envSnapshot.NEON_AI_GATEWAY_TOKEN),
    ok: false,
  };
  if (envSnapshot.NEON_AI_GATEWAY_BASE_URL && envSnapshot.NEON_AI_GATEWAY_TOKEN) {
    const modelsUrl = `${envSnapshot.NEON_AI_GATEWAY_BASE_URL.replace(/\/$/, "")}/v1/models`;
    try {
      const resp = await fetch(modelsUrl, {
        headers: {
          Authorization: `Bearer ${envSnapshot.NEON_AI_GATEWAY_TOKEN}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });
      const rawText = await resp.text();
      let bodyData: unknown = rawText;
      try {
        bodyData = JSON.parse(rawText);
      } catch {
        // leave as text
      }
      aiGatewayStatus = {
        configured: true,
        reachable: true,
        authenticated: resp.status !== 401,
        ok: [200, 402, 403, 404].includes(resp.status),
        base_url: envSnapshot.NEON_AI_GATEWAY_BASE_URL,
        endpoint_tested: modelsUrl,
        status_code: resp.status,
        gateway_response: bodyData,
      };
    } catch (err) {
      aiGatewayStatus = {
        configured: true,
        reachable: false,
        ok: false,
        base_url: envSnapshot.NEON_AI_GATEWAY_BASE_URL,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  return NextResponse.json({
    branch: envSnapshot.NEON_BRANCH || "production",
    branch_id: envSnapshot.NEON_BRANCH_ID || null,
    services: {
      postgres: postgresStatus,
      auth: authStatus,
      functions: functionsStatus,
      realtime: realtimeStatus,
      ai_gateway: aiGatewayStatus,
    },
  });
}
