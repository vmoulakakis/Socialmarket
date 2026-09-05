import { notFound } from 'next/navigation';
import { affinityProducts, bySlug } from '../data';
import { affiliateRecords } from '../records';
import ConversionPage from '../ConversionPage';

export function generateStaticParams() {
  return affinityProducts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const p = bySlug[slug];
  if (!p) return {};
  return {
    title: `${p.shortName} | AFFINITY B2B`,
    description: p.subheadline,
    robots: { index: true, follow: true },
    openGraph: { title: p.shortName, description: p.subheadline, type: 'website' },
  };
}

export default async function ProductPage({ params }) {
  const { slug } = await params;
  const product = bySlug[slug];
  if (!product) notFound();
  const record = affiliateRecords[product.aliexpressId];
  if (!record?.promotionLink) notFound();
  return <ConversionPage product={product} record={record} />;
}
