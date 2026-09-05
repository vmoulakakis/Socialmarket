import './globals.css';

export const metadata = {
  metadataBase: new URL('https://eu-solution-foundry.vercel.app'),
  title: {
    default: 'EU Solution Foundry | Smart B2B Buying',
    template: '%s | EU Solution Foundry',
  },
  description: 'B2B sourcing, landed-cost analysis, ROI and due diligence for professional equipment buyers in Greece and Europe.',
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }) {
  return (
    <html lang="el">
      <body>{children}</body>
    </html>
  );
}
