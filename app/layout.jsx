import './globals.css';
import Link from 'next/link';
import AuthGate from '@/components/AuthGate';

export const metadata = {
  title: 'SocialMarket AI',
  description: 'Greek Market & Affiliate Business Intelligence'
};

export default function RootLayout({ children }) {
  return (
    <html lang="el">
      <body>
        <div className="shell">
          <nav className="nav">
            <Link className="brand" href="/analytics">SocialMarket AI</Link>
            <div className="navlinks">
              <Link href="/analytics">Analytics</Link>
              <Link href="/optimization">Optimize</Link>
              <Link href="/">AI Console</Link>
              <Link href="/market">Market Map</Link>
              <Link href="/niches">Niches</Link>
              <Link href="/merchants">Merchants</Link>
              <Link href="/products">Products</Link>
              <Link href="/configuration">Configuration</Link>
              <Link href="/creatives">Creatives</Link>
              <Link href="/scheduler">Publishing</Link>
            </div>
          </nav>
          <AuthGate>{children}</AuthGate>
        </div>
      </body>
    </html>
  );
}
