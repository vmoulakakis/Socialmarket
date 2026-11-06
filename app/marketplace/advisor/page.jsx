import ShopExperience from '@/components/shop/ShopExperience';
export const metadata={
 title:'AI Shopping Advisor | SocialMarket AI',
 description:'Ο AI Shopping Advisor ερευνά πραγματικές καταχωρίσεις και ξεχωρίζει τα επαληθευμένα στοιχεία από όσα απαιτούν έλεγχο.',
 robots:{index:false,follow:true}
};
export default function BuyerAdvisorPage(){return <ShopExperience initialChat/>;}
