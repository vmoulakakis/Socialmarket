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
 const categories=new Map(),programs=new Map();
 let withImage=0,withTracking=0;
 for(const p of rows){const cat=String(p.category||"(missing)").slice(0,90),program=String(p.program_name||"(missing)").slice(0,90);categories.set(cat,(categories.get(cat)||0)+1);programs.set(program,(programs.get(program)||0)+1);if(p.image_url||p.thumb_url)withImage++;if(p.tracking_url)withTracking++}
 const top=m=>[...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,16);
 console.log("CARCARE_FEED_AUDIT categories",JSON.stringify(top(categories)));
 console.log("CARCARE_FEED_AUDIT programs",JSON.stringify(top(programs)));
 console.log("CARCARE_FEED_AUDIT media",withImage,"tracking",withTracking);
 console.log("CARCARE_FEED_AUDIT samples",JSON.stringify(rows.slice(0,12).map(p=>({title:String(p.product_name||p.model_name||"").slice(0,100),category:String(p.category||"").slice(0,70),price:p.price,program:p.program_name}))));
}catch(e){console.log("CARCARE_FEED_AUDIT error",e?.name||"Error",String(e?.message||"").slice(0,120))}
