import BuyerAdvisor from '@/components/catalog/BuyerAdvisor';
export const metadata = {
  title: 'Έξυπνη διερεύνηση αγορών | SocialMarket AI',
  description: 'Περιέγραψε την ανάγκη σου. Δες υποψήφιες αντιστοιχίσεις από πραγματικό affiliate feed, με σαφή έλεγχο της αξιοπιστίας των στοιχείων.',
  robots: { index: false, follow: false },
};
export default function BuyerAdvisorPage() {
  return <BuyerAdvisor />;
}
