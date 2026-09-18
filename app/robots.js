export default function robots() {
  return {
    rules: [
      { userAgent: '*', allow: ['/marketplace','/marketplace/','/luxecorner','/luxecorner/'], disallow: ['/admin','/configuration','/analytics','/scheduler','/products','/merchants','/demand','/forecast-products','/niches','/creatives','/optimization','/market','/api/'] },
    ],
    sitemap: 'https://socialmarket-theta.vercel.app/sitemap.xml',
    host: 'https://socialmarket-theta.vercel.app',
  };
}
