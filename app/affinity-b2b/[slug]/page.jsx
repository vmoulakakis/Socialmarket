import { notFound } from 'next/navigation';
import { affinityProducts, bySlug } from '../data';
import { affiliateRecords } from '../records';
import ConversionPage from '../ConversionPage';

const BASE = 'https://socialmarket-theta.vercel.app';

export function generateStaticParams() {
  return affinityProducts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const p = bySlug[slug];
  if (!p) return {};
  const canonical = `${BASE}/affinity-b2b/${slug}`;
  return {
    metadataBase: new URL(BASE),
    title: `${p.shortName} για B2B | Κόστος, ROI & Αγορά στην Ελλάδα`,
    description: `${p.subheadline} Αναλυτικός B2B οδηγός αγοράς με landed-cost calculator, τεχνικό fit, seller checks, warranty και σύγκριση κόστους.`,
    alternates: { canonical },
    robots: { index: true, follow: true, googleBot: { index: true, follow: true, 'max-image-preview': 'large', 'max-snippet': -1 } },
    openGraph: { title: `${p.shortName} | B2B Buying Guide`, description: p.subheadline, type: 'website', url: canonical },
    twitter: { card: 'summary_large_image', title: p.shortName, description: p.subheadline },
  };
}

export default async function ProductPage({ params }) {
  const { slug } = await params;
  const product = bySlug[slug];
  if (!product) notFound();
  const raw = affiliateRecords[product.aliexpressId];
  if (!raw?.promotionLink) notFound();

  const record = {
    aliexpressId: raw.aliexpressId,
    salePrice: raw.salePrice,
    salePriceCurrency: raw.salePriceCurrency,
    shopName: raw.shopName,
    mainImage: raw.mainImage,
    updatedAt: raw.updatedAt,
    promotionLink: `/go/${slug}`,
    detailUrl: `https://www.aliexpress.com/item/${product.aliexpressId}.html`,
  };

  const canonical = `${BASE}/affinity-b2b/${slug}`;
  const faq = product.faq.map(([name, text]) => ({ '@type': 'Question', name, acceptedAnswer: { '@type': 'Answer', text } }));
  const schema = [
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: `${product.shortName} B2B Buying Guide`,
      url: canonical,
      inLanguage: 'el-GR',
      description: product.subheadline,
      primaryImageOfPage: raw.mainImage ? { '@type': 'ImageObject', contentUrl: raw.mainImage } : undefined,
      about: { '@type': 'Product', name: product.shortName, description: product.subheadline },
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faq,
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'B2B Ευκαιρίες', item: `${BASE}/affinity-b2b` },
        { '@type': 'ListItem', position: 2, name: product.shortName, item: canonical },
      ],
    },
  ];

  return <>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
    <ConversionPage product={product} record={record} />
  </>;
}
