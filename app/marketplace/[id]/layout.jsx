import {getLuxeProduct} from '@/lib/luxecorner';
export async function generateMetadata({params}){
 const {id}=await params;
 const p=await getLuxeProduct(id);
 return p?{title:`${p.product_name} | SocialMarket`,description:`${p.product_name} · ${p.program_name}. Δες πληροφορίες και προσφορά στο συνεργαζόμενο κατάστημα.`}:{title:'Προϊόν δεν βρέθηκε',robots:{index:false}};
}
export default function Layout({children}){return children;}
