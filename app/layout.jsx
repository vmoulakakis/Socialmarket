import './globals.css';
import Link from 'next/link';
import AuthGate from '@/components/AuthGate';

export const metadata={title:'SocialMarket AI',description:'Autonomous affiliate social marketing engine'};

export default function RootLayout({children}){
  return <html lang="el"><body><div className="shell">
    <nav className="nav"><Link className="brand" href="/">SocialMarket AI</Link><div className="navlinks"><Link href="/market">Market Map</Link><Link href="/niches">Niches</Link><Link href="/merchants">Merchants</Link><Link href="/products">Products</Link><Link href="/product-to-post">Product → Post</Link><Link href="/monitor">Monitor</Link><Link href="/creatives">Creatives</Link><Link href="/scheduler">Social Scheduler</Link><Link href="/tiktok">TikTok Studio</Link></div></nav>
    <AuthGate>{children}</AuthGate>
  </div></body></html>
}
