import './globals.css';
import './semantic.css';
import './design-v2.css';
import AuthGate from '@/components/AuthGate';
import AppShell from '@/components/AppShell';

export const metadata = {
  title: 'SocialMarket AI',
  description: 'Greek Market & Affiliate Business Intelligence'
};

export default function RootLayout({ children }) {
  return (
    <html lang="el">
      <body>
        <AuthGate>
          <AppShell>{children}</AppShell>
        </AuthGate>
      </body>
    </html>
  );
}
