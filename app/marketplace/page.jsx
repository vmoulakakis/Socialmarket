import Catalog from '@/components/catalog/Catalog';
import {getLuxeTop100} from '@/lib/luxecorner';
export const metadata={title:'SocialMarket | Προϊόντα για το σπίτι'};
export default async function Page(){
 let products=[],error=false;
 try{products=await getLuxeTop100();}catch{error=true;}
 return <Catalog products={products.map(({source_product_id,product_name,price_eur,program_name,image_url,tracking_url,category_raw})=>({source_product_id,product_name,price_eur,program_name,image_url,tracking_url,category_raw}))} error={error}/>;
}
