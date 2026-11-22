import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const ALLOWED_OUTBOUND_HEADERS = [
  "cookie",
  "content-type",
  "accept",
  "accept-language",
  "authorization",
  "x-requested-with",
] as const;

const STRIPPED_RESPONSE_HEADERS = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "transfer-encoding",
]);

const RETRYABLE_GET_STATUSES = new Set([502, 503, 504]);

function resolveBackendBase(): string {
  const raw = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").trim();
  return (/^https?:\/\//i.test(raw) ? raw : `http://${raw}`).replace(/\/+$/, "");
}

function sanitizeSetCookie(cookieHeader: string): string {
  // Strip any upstream Domain=... attribute so cookies bind cleanly to the frontend origin.
  return cookieHeader.replace(/;\s*Domain=[^;]*/gi, "");
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function proxyToBackend(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const backendBase = resolveBackendBase();

  // Safety guard: prevent self-proxy loops if BACKEND_INTERNAL_URL points back to the frontend host
  try {
    const backendUrl = new URL(backendBase);
    const incomingHost = (
      req.headers.get("x-forwarded-host") ||
      req.headers.get("host") ||
      req.nextUrl.host ||
      ""
    )
      .split(",")[0]
      .trim()
      .toLowerCase();
    if (incomingHost && backendUrl.host.toLowerCase() === incomingHost) {
      return NextResponse.json(
        {
          detail: `Proxy misconfiguration: BACKEND_INTERNAL_URL (${backendUrl.host}) matches incoming frontend host (${incomingHost}), which would cause a 508 redirect loop. Point BACKEND_INTERNAL_URL to the FastAPI backend service URL.`,
        },
        { status: 502 }
      );
    }
  } catch {
    return NextResponse.json(
      { detail: `Invalid BACKEND_INTERNAL_URL configuration: "${backendBase}"` },
      { status: 502 }
    );
  }

  const { path } = await context.params;
  const search = req.nextUrl.search || "";
  const targetUrl = `${backendBase}/api/${path.join("/")}${search}`;

  // Explicit allowlist only — never forward Cloudflare/Render hop & loop detection headers
  // (cdn-loop, cf-*, render-proxy-ttl, host, via, x-forwarded-*, forwarded, connection, content-length).
  const forwardHeaders = new Headers();
  for (const headerName of ALLOWED_OUTBOUND_HEADERS) {
    const val = req.headers.get(headerName);
    if (val) {
      forwardHeaders.set(headerName, val);
    }
  }

  const method = req.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await req.arrayBuffer() : undefined;

  const maxAttempts = method === "GET" ? 2 : 1;
  let upstream: Response | null = null;
  let lastError: unknown = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      upstream = await fetch(targetUrl, {
        method,
        headers: forwardHeaders,
        body: body && body.byteLength > 0 ? body : undefined,
        redirect: "manual",
        cache: "no-store",
      });

      if (
        attempt < maxAttempts &&
        RETRYABLE_GET_STATUSES.has(upstream.status)
      ) {
        // Drain body before retrying on Render Free cold-start 502/503/504
        try {
          await upstream.arrayBuffer();
        } catch {
          // ignore drain error
        }
        await sleep(750 * attempt);
        continue;
      }
      break;
    } catch (err) {
      lastError = err;
      if (attempt < maxAttempts) {
        await sleep(750 * attempt);
        continue;
      }
    }
  }

  if (!upstream) {
    const errMsg =
      lastError instanceof Error ? lastError.message : "Upstream backend unreachable";
    return NextResponse.json(
      {
        detail: `Backend service is unreachable or waking up (${errMsg}). Please retry in a few seconds.`,
      },
      { status: 502 }
    );
  }

  const respHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (STRIPPED_RESPONSE_HEADERS.has(lower)) {
      return;
    }
    if (lower === "set-cookie") {
      respHeaders.append(key, sanitizeSetCookie(value));
    } else {
      respHeaders.set(key, value);
    }
  });

  // Preserve multiple Set-Cookie headers when supported by undici/Node 22
  const getSetCookie = (
    upstream.headers as Headers & { getSetCookie?: () => string[] }
  ).getSetCookie;
  if (typeof getSetCookie === "function") {
    const cookies = getSetCookie.call(upstream.headers);
    if (cookies.length > 0) {
      respHeaders.delete("set-cookie");
      for (const c of cookies) {
        respHeaders.append("set-cookie", sanitizeSetCookie(c));
      }
    }
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export const GET = proxyToBackend;
export const POST = proxyToBackend;
export const PUT = proxyToBackend;
export const PATCH = proxyToBackend;
export const DELETE = proxyToBackend;
export const OPTIONS = proxyToBackend;
