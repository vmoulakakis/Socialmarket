import { NextResponse } from 'next/server';

const PUBLIC_PREFIXES = [
  '/affinity-b2b',
  '/go/',
  '/robots.txt',
  '/sitemap.xml',
  '/favicon.ico',
  '/_next/',
];

export function middleware(request) {
  const { pathname } = request.nextUrl;

  if (pathname === '/' || PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  return new NextResponse('Not Found', {
    status: 404,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'X-Robots-Tag': 'noindex, nofollow',
      'Cache-Control': 'no-store',
    },
  });
}

export const config = {
  matcher: ['/((?!_next/static|_next/image).*)'],
};
