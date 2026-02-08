import { NextRequest, NextResponse } from "next/server";

const DEFAULT_BASE_URL = "http://127.0.0.1:8844";

function buildTargetUrl(pathSegments: string[], request: NextRequest): URL {
  const base = (process.env.CDI_API_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/$/, "");
  const upstreamPath = pathSegments.join("/");
  const url = new URL(`${base}/${upstreamPath}`);
  url.search = request.nextUrl.search;
  return url;
}

async function proxy(request: NextRequest, pathSegments: string[]): Promise<NextResponse> {
  const url = buildTargetUrl(pathSegments, request);
  const apiToken = process.env.CDI_API_TOKEN;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (apiToken) {
    headers.set("X-API-Token", apiToken);
  }

  const isBodyMethod = !["GET", "HEAD"].includes(request.method.toUpperCase());
  const body = isBodyMethod ? await request.text() : undefined;

  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body: body && body.length > 0 ? body : undefined,
    cache: "no-store"
  });

  const upstreamBody = await upstream.text();
  const responseHeaders = new Headers();
  const upstreamResponseType = upstream.headers.get("content-type") ?? "application/json";
  responseHeaders.set("content-type", upstreamResponseType);

  return new NextResponse(upstreamBody, {
    status: upstream.status,
    headers: responseHeaders
  });
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }): Promise<NextResponse> {
  return proxy(request, context.params.path);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }): Promise<NextResponse> {
  return proxy(request, context.params.path);
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }): Promise<NextResponse> {
  return proxy(request, context.params.path);
}

export async function PATCH(request: NextRequest, context: { params: { path: string[] } }): Promise<NextResponse> {
  return proxy(request, context.params.path);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }): Promise<NextResponse> {
  return proxy(request, context.params.path);
}
