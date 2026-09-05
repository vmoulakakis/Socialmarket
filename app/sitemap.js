import { affinityProducts } from './affinity-b2b/data';

const BASE = 'https://socialmarket-theta.vercel.app';

export default function sitemap() {
  const now = new Date();
  return [
    { url: `${BASE}/affinity-b2b`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    ...affinityProducts.map((p) => ({
      url: `${BASE}/affinity-b2b/${p.slug}`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.8,
    })),
  ];
}
