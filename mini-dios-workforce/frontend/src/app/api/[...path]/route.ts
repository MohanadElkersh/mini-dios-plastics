import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

function resolveBackendBase(): string {
  const raw = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").trim();
  return (/^https?:\/\//i.test(raw) ? raw : `http://${raw}`).replace(/\/+$/, "");
}

async function proxyToBackend(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  const search = req.nextUrl.search || "";
  const targetUrl = `${resolveBackendBase()}/api/${path.join("/")}${search}`;

  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "host" || lower === "connection" || lower === "content-length") {
      return;
    }
    forwardHeaders.set(key, value);
  });

  const method = req.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await req.arrayBuffer() : undefined;

  const upstream = await fetch(targetUrl, {
    method,
    headers: forwardHeaders,
    body: body && body.byteLength > 0 ? body : undefined,
    redirect: "manual",
  });

  const respHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "transfer-encoding" || lower === "connection" || lower === "content-encoding") {
      return;
    }
    if (lower === "set-cookie") {
      respHeaders.append(key, value);
    } else {
      respHeaders.set(key, value);
    }
  });

  // Preserve multiple Set-Cookie headers when supported by undici/Node 22
  const getSetCookie = (upstream.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof getSetCookie === "function") {
    const cookies = getSetCookie.call(upstream.headers);
    if (cookies.length > 0) {
      respHeaders.delete("set-cookie");
      for (const c of cookies) {
        respHeaders.append("set-cookie", c);
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
