import Catalog from '@/components/catalog/Catalog';
import {getLuxeTop100} from '@/lib/luxecorner';
export const metadata={title:'SocialMarket | Προϊόντα για το σπίτι'};
export default async function Page(){
 let products=[],error=false;
 try{products=await getLuxeTop100();}catch{error=true;}
 return <Catalog products={products} error={error}/>;
}
