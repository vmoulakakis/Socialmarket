import {normalizeFeed,PROBLEMS,scoreMatch} from "../lib/catalog.mjs";
// Server-only deployment feed audit. No URLs, IDs or credentials are logged.
const url=process.env.LINKWISE_CARCARE_FEED_URL;
if(!url){console.log("CARCARE_FEED_AUDIT: missing LINKWISE_CARCARE_FEED_URL");process.exit(0)}
try{
 const u=new URL(url);
 if(u.protocol!=="https:"||u.hostname!=="affiliate.linkwi.se")throw Error("unexpected_feed_hostname");
 const resp=await fetch(u.href,{signal:AbortSignal.timeout(45000),headers:{accept:"application/json"}});
 console.log("CARCARE_FEED_AUDIT status",resp.status,"type",resp.headers.get("content-type")||"unknown");
 if(!resp.ok)process.exit(0);
 const raw=await resp.text();
 console.log("CARCARE_FEED_AUDIT bytes",Buffer.byteLength(raw));
 let doc;try{doc=JSON.parse(raw)}catch{console.log("CARCARE_FEED_AUDIT invalid JSON");process.exit(0)}
 const rows=Array.isArray(doc)?doc:Array.isArray(doc.products)?doc.products:Array.isArray(doc.items)?doc.items:Array.isArray(doc.data)?doc.data:Array.isArray(doc.product)?doc.product:[];
 console.log("CARCARE_FEED_AUDIT keys",Array.isArray(doc)?"array":Object.keys(doc).slice(0,16).join(","));
 console.log("CARCARE_FEED_AUDIT total",rows.length);
 const valid=normalizeFeed(doc);
 const groups=Object.fromEntries(Object.keys(PROBLEMS).map(k=>[k,valid.filter(p=>scoreMatch(p,k)>0).length]));
 console.log("CARCARE_LIVE_ELIGIBLE",valid.length,"solution_groups",JSON.stringify(groups));
 console.log("CARCARE_LIVE_ELIGIBLE_SAMPLE",JSON.stringify(valid.slice(0,10).map(p=>({title:p.title.slice(0,65),price:p.price,category:p.category.slice(0,55),merchant:p.merchant}))));

 const categories=new Map(),programs=new Map();
 let withImage=0,withTracking=0;
 for(const p of rows){const cat=String(p.category||"(missing)").slice(0,90),program=String(p.program_name||"(missing)").slice(0,90);categories.set(cat,(categories.get(cat)||0)+1);programs.set(program,(programs.get(program)||0)+1);if(p.image_url||p.thumb_url)withImage++;if(p.tracking_url)withTracking++}
 const top=m=>[...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,16);
 console.log("CARCARE_FEED_AUDIT categories",JSON.stringify(top(categories)));
 console.log("CARCARE_FEED_AUDIT programs",JSON.stringify(top(programs)));
 console.log("CARCARE_FEED_AUDIT media",withImage,"tracking",withTracking);
 const automotive=rows.filter(p=>/αυτοκιν|car accessories|vehicle|motor|οχημ|οχημ|υαλοκαθαρισ|ελαστικ|ζαντ|λάμπες|αξεσουάρ αυτοκιν|car care|car wash|φορτιστ.*αυτοκιν|gadgets αυτοκιν/i.test(String(p.category||"")));
 const autoCats=new Map();for(const p of automotive){const category=String(p.category||"").replace(/&(?:amp;)?gt;/g,">").replace(/&(?:amp;)?amp;/g,"&").slice(0,140);autoCats.set(category,(autoCats.get(category)||0)+1)}
 console.log("CARCARE_AUTO_AUDIT count",automotive.length,"categories",JSON.stringify([...autoCats.entries()].sort((a,b)=>b[1]-a[1]).slice(0,38)));
 console.log("CARCARE_AUTO_AUDIT first_product_keys",JSON.stringify(Object.keys(rows[0]||{})));
 console.log("CARCARE_AUTO_AUDIT products_sample",JSON.stringify(automotive.slice(0,45).map(p=>({name:String(p.product_name||"").slice(0,95),category:String(p.category||"").slice(0,85),price:p.price,in_stock:p.in_stock,availability:p.availability,valid_to:p.valid_to,source:p.program_name}))));
 const textGroups={wipers:/υαλοκαθαρισ|wiper/i,bulbs:/λαμπ|λάμπ|led|headlight|h7|h4/i,cleaners:/καθαρισ|σφουγγ|πλυσ|γυαλισ|κερ|polish|wax|microfiber|μικροιν/i,electrical:/μπαταρ|φορτιστ|διακοπτ|ρελε|αισθητ|charger|switch|sensor/i,gadgets:/gadgets|κάμερα|camera|holder|gps|bluetooth|usb/i};
 for(const [group,re] of Object.entries(textGroups)){const hits=automotive.filter(p=>re.test(String(p.product_name||"")+" "+String(p.category||"")));console.log("CARCARE_AUTO_AUDIT group",group,hits.length,JSON.stringify(hits.slice(0,6).map(p=>({title:String(p.product_name||"").slice(0,85),price:p.price,category:String(p.category||"").slice(0,75)}))))}
 console.log("CARCARE_FEED_AUDIT samples",JSON.stringify(rows.slice(0,12).map(p=>({title:String(p.product_name||p.model_name||"").slice(0,100),category:String(p.category||"").slice(0,70),price:p.price,program:p.program_name}))));
}catch(e){console.log("CARCARE_FEED_AUDIT error",e?.name||"Error",String(e?.message||"").slice(0,120))}
