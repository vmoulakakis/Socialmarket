export const metadata = {
  title: 'SocialMarket — Λύσεις που αξίζουν για την Ελλάδα',
  description: 'Semantic marketplace με επιλεγμένες λύσεις για πραγματικές ανάγκες, ελεγμένες με AI research, market-gap evidence και quality gates.',
  robots: { index: true, follow: true, noarchive: false, nosnippet: false },
  alternates: { canonical: '/marketplace' },
  openGraph: {
    title: 'SocialMarket — Μην ψάχνεις προϊόν. Βρες τη σωστή λύση.',
    description: 'Pain-first marketplace για την ελληνική αγορά, με evidence-first AI επιλογή.',
    type: 'website',
    locale: 'el_GR',
  },
};

export default function MarketplaceLayout({children}){return children;}
