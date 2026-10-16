export const metadata = {
  title: 'SocialMarket — Προσεκτικά επιλεγμένες λύσεις',
  description: 'Σύγκρινε προϊόντα από την διαθέσιμη συλλογή, έλεγξε τιμές και χαρακτηριστικά πριν επισκεφτείς το συνεργαζόμενο κατάστημα.',
  robots: { index: true, follow: true, noarchive: false, nosnippet: false },
  alternates: { canonical: '/marketplace' },
  openGraph: {
    title: 'SocialMarket — Επιλογές με ξεκάθαρα κριτήρια',
    description: 'Επιλεγμένες προτάσεις και ξεκάθαρος οδηγός αγοράς για τον χώρο σου.',
    type: 'website',
    locale: 'el_GR',
    siteName: 'SocialMarket',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SocialMarket — Προσεκτικά επιλεγμένες λύσεις',
    description: 'Επιλογές με σαφή κριτήρια.',
  },
};

export default function MarketplaceLayout({children}){return children;}
