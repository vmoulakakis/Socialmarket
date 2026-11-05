import {NextResponse} from "next/server";
import {createClient} from "@supabase/supabase-js";
import {normalizeFeed,selectProducts,PROBLEMS} from "../../../lib/catalog.mjs";
export const runtime="nodejs";
export const dynamic="force-dynamic";
const fold=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const rules=[
 ["visibility",["υαλοκαθαρισ","παρμπριζ","βροχ","ορατοτ"]],
 ["lighting",["φως","φωτα","λαμπ","φαναρ","h7"]],
 ["cleaning",["καθαρισ","λεκε","πλυσ","γυαλισ","γρατζουν"]],
 ["electrical",["παραθυρ","διακοπτ","κλειδωμ","αισθητ"]],
 ["gadgets",["φορτιστ","bluetooth","usb","καμερα","παρκαρισ"]],
 ["maintenance",["μπαταρ","συντηρησ","λαδι","φιλτρ","φρεν"]]
];
const guidance={
 visibility:"Έλεγξε το μήκος και τον μηχανισμό σύνδεσης των υαλοκαθαριστήρων. Μην οδηγείς με ανεπαρκή ορατότητα.",
 lighting:"Επιβεβαίωσε τύπο λάμπας, ισχύ και έγκριση. Δεν είναι κάθε LED μετατροπή κατάλληλη ή νόμιμη.",
 cleaning:"Ξεκίνα με ήπιο καθαρισμό και δοκιμή σε μικρή περιοχή. Μη χρησιμοποιείς ασύμβατα χημικά.",
 electrical:"Πριν αγοράσεις ανταλλακτικό, σύγκρινε OEM κωδικό, μοντέλο και έτος. Για ηλεκτρικές εργασίες απευθύνσου σε τεχνικό.",
 gadgets:"Έλεγξε τις απαιτήσεις τροφοδοσίας και εγκατάστασης. Μην εμποδίζεις την ορατότητα ή τους αερόσακους.",
 maintenance:"Ακολούθησε τις εργοστασιακές προδιαγραφές και το πρόγραμμα συντήρησης. Η συμβατότητα δεν επαληθεύεται από λέξεις-κλειδιά."
};
export async function POST(request){
 try{
  if(Number(request.headers.get("content-length")||0)>4096)return NextResponse.json({error:"Πολύ μεγάλο αίτημα."},{status:413});
  const body=await request.json(),question=String(body.question||"").trim().slice(0,240);
  if(question.length<4)return NextResponse.json({error:"Περιέγραψε το πρόβλημα με λίγες λέξεις."},{status:400});
  const text=fold(question);
  const isOther=/ασφαλεια κατοικιας|ασφαλεια υγειας|δανειο|τραπεζ|ασφαλιστρ|ασφαλεια αυτοκινητου|insurance/i.test(text);
  if(isOther)return NextResponse.json({answer:"Αυτή η κατηγορία δεν έχει σήμερα ενεργές επαληθευμένες προσφορές στο νέο Linkwise feed. Δεν εμφανίζονται ενδεικτικές τιμές ως πραγματικές.",products:[],source:"none",problem:null,mode:"no-data"});
  let problem=PROBLEMS[body.problem]?body.problem:null;
  if(!problem){const ranked=rules.map(([id,words])=>({id,hits:words.filter(w=>text.includes(fold(w))).length})).sort((a,b)=>b.hits-a.hits);problem=ranked[0].hits?ranked[0].id:"maintenance"}
  let products=[],source="none";
  const dbUrl=process.env.NEXT_PUBLIC_CARCARE_SUPABASE_URL,anon=process.env.CARCARE_SUPABASE_ANON_KEY;
  if(dbUrl&&anon){
   const db=createClient(dbUrl,anon,{auth:{persistSession:false}});
   const {data}=await db.from("carcare_ai_products").select("id,source_product_id,title,category,brand,merchant,price_eur,image_url,tracking_url,inferred_problems")
    .eq("is_published",true).eq("in_stock",true).contains("inferred_problems",[problem]).order("price_eur",{ascending:true}).limit(60);
   if(data?.length){products=data.map(p=>({id:p.source_product_id,title:p.title,category:p.category,brand:p.brand,merchant:p.merchant,price:p.price_eur,image_url:p.image_url,tracking_url:p.tracking_url}));source="VMDB"}
  }
  if(!products.length&&process.env.LINKWISE_CARCARE_FEED_URL){
   const resp=await fetch(process.env.LINKWISE_CARCARE_FEED_URL,{next:{revalidate:3600},signal:AbortSignal.timeout(38000)});
   if(resp.ok){products=selectProducts(normalizeFeed(await resp.json()),{problem,limit:24});if(products.length)source="Linkwise"}
  }
  const answer=guidance[problem]+" "+(products.length?"Οι παρακάτω λύσεις είναι θεματικά σχετικές, όχι πιστοποιημένα συμβατές με το όχημά σου.":"Δεν υπάρχουν προς το παρόν επιβεβαιωμένα ενεργά προϊόντα που να ταιριάζουν.");
  return NextResponse.json({answer,problem,products:products.slice(0,6),source,mode:"evidence_retrieval",agent_roles:["Intent Router","Catalog Analyst","Safety Critic"],caution:"Όχι ιατρική, ασφαλιστική ή τεχνική διάγνωση. Επιβεβαίωσε προδιαγραφές πριν αγοράσεις."},{headers:{"Cache-Control":"no-store"}});
 }catch(error){console.error("CarCare assistant:",String(error.message).slice(0,80));return NextResponse.json({error:"Προσωρινά δεν είναι διαθέσιμη η αναζήτηση."},{status:503})}
}
