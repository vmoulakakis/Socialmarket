const BASE = 'https://socialmarket-theta.vercel.app';

export default function robots() {
  return {
    rules: [
      { userAgent: '*', allow: ['/affinity-b2b/', '/affinity-b2b'], disallow: ['/go/', '/api/', '/configuration', '/scheduler'] },
    ],
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
