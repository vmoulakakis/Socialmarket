import { NextResponse } from 'next/server';
import { bySlug } from '../../affinity-b2b/data';
import { affiliateRecords } from '../../affinity-b2b/records';

export const dynamic = 'force-dynamic';

export async function GET(request, { params }) {
  const { slug } = await params;
  const product = bySlug[slug];
  if (!product) return NextResponse.redirect(new URL('/affinity-b2b', request.url), 302);
  const record = affiliateRecords[product.aliexpressId];
  const target = record?.promotionLink || `https://www.aliexpress.com/item/${product.aliexpressId}.html`;
  const res = NextResponse.redirect(target, 302);
  res.headers.set('Cache-Control', 'no-store, max-age=0');
  res.headers.set('X-Robots-Tag', 'noindex, nofollow');
  return res;
}
