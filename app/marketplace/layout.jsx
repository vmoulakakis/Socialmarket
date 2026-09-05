export const metadata = {
  title: 'SocialMarket — Βρες αυτό που λύνει το πρόβλημα',
  description: 'Social discovery marketplace με curated problem-solvers για πραγματικές ανάγκες: λιγότερη τριβή, περισσότερος χρόνος, πιο έξυπνη καθημερινότητα.',
  robots: { index: true, follow: true, noarchive: false, nosnippet: false },
  alternates: { canonical: '/marketplace' },
  openGraph: {
    title: 'SocialMarket — Something annoying you? Find what fixes it.',
    description: 'Pain-first social marketplace με curated λύσεις που ξεκινούν από πραγματικό πρόβλημα και use case.',
    type: 'website',
    locale: 'el_GR',
  },
};

export default function MarketplaceLayout({children}){return children;}
