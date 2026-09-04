import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AliExpress EU Local Day Deals | Europe Offers & Buyer Guide',
  description: 'Explore AliExpress EU Local Day offers with a practical buyer checklist for Europe. Compare final price, shipping, seller quality, returns and product fit before buying.',
  keywords: ['AliExpress EU Local Day','AliExpress Europe deals','EU warehouse deals','AliExpress Greece','AliExpress offers Europe'],
  alternates: { canonical: '/eu-local-day' },
  openGraph: { title: 'AliExpress EU Local Day Deals | Europe Buyer Guide', description: 'A smarter route into AliExpress EU Local Day: check final price, delivery, returns and seller quality before you buy.', type: 'website', url: '/eu-local-day' },
  twitter: { card: 'summary_large_image', title: 'AliExpress EU Local Day Deals', description: 'Explore EU Local Day with a practical Europe-focused buyer checklist.' },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, 'max-image-preview': 'large', 'max-snippet': -1 } },
};

export default function EuLocalDayLayout({children}:{children:React.ReactNode}) { return children; }
