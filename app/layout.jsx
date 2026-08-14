import './globals.css';
import Link from 'next/link';
import AuthGate from '@/components/AuthGate';

export const metadata={title:'SocialMarket AI',description:'Greek Hidden Opportunity Engine'};

export default function RootLayout({children}){
  return <html lang="el"><body><div className="shell">
    <nav className="nav"><Link className="brand" href="/">SocialMarket AI</Link><div className="navlinks"><Link href="/sites">Brands & Sites</Link><Link href="/market">Market Map</Link><Link href="/niches">Niches</Link><Link href="/merchants">Merchants</Link><Link href="/products">Products</Link><Link href="/creatives">Creatives</Link><Link href="/scheduler">Publishing Outbox</Link></div></nav>
    <AuthGate>{children}</AuthGate>
  </div></body></html>
}
