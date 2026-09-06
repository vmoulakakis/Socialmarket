export const metadata = {
  title: 'AFFINITY — Small Solutions. A Better You.',
  description: 'Premium problem-solving eShop με curated λύσεις για πραγματικές καθημερινές ανάγκες. Ανακάλυψε προϊόντα μέσα από pain, gap, solution και ξεκάθαρα buyer checks.',
  robots: { index: true, follow: true, noarchive: false, nosnippet: false },
  alternates: { canonical: '/marketplace' },
  openGraph: {
    title: 'AFFINITY — Discover products that solve real problems.',
    description: 'Curated problem-solving eShop για μια πιο εύκολη, όμορφη και οργανωμένη καθημερινότητα.',
    type: 'website',
    locale: 'el_GR',
    siteName: 'AFFINITY',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AFFINITY — Small Solutions. A Better You.',
    description: 'Discover products that solve real problems.',
  },
};

export default function MarketplaceLayout({children}){return children;}
