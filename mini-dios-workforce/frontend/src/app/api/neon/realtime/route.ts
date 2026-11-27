import { NextRequest, NextResponse } from "next/server";
import { sealCheckpointsLiveQuery } from "@/lib/neon";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  try {
    const sandboxId = req.nextUrl.searchParams.get("sandbox_id") || "local";
    const limit = Math.min(50, Math.max(1, Number(req.nextUrl.searchParams.get("limit") || "25")));
    const { database, realtimeUrl, sealedQuery } = await sealCheckpointsLiveQuery(sandboxId, limit);
    return NextResponse.json({
      ok: true,
      sandbox_id: sandboxId,
      database,
      realtimeUrl,
      sealedQuery,
    });
  } catch (err) {
    return NextResponse.json(
      {
        ok: false,
        error: err instanceof Error ? err.message : "Failed to seal Neon Realtime live query.",
      },
      { status: 500 }
    );
  }
}
