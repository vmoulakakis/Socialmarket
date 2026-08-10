import './globals.css';
import Link from 'next/link';
export const metadata={title:'SocialMarket AI',description:'Greek Hidden Opportunity Engine'};
export default function RootLayout({children}){return <html lang="el"><body><div className="shell"><nav className="nav"><Link className="brand" href="/">SocialMarket AI</Link><div className="navlinks"><Link href="/market">Market Map</Link><Link href="/products">Products</Link><Link href="/creatives">Creatives</Link></div></nav>{children}</div></body></html>}
