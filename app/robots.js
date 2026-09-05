const BASE = 'https://eu-solution-foundry.vercel.app';

export default function robots() {
  return {
    rules: [{ userAgent: '*', allow: '/', disallow: ['/go/'] }],
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
