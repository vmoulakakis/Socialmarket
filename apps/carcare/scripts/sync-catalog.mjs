import {normalizeFeed} from "../lib/catalog.mjs";
const source=process.env.LINKWISE_CARCARE_FEED_URL;
if(!source)throw Error("missing feed");
const response=await fetch(source,{signal:AbortSignal.timeout(70000)});
if(!response.ok)throw Error("invalid feed response");
const products=normalizeFeed(await response.json());
console.log("CarCare eligible imported candidate count",products.length);

const base=process.env.NEXT_PUBLIC_CARCARE_SUPABASE_URL;
const syncKey=process.env.CARCARE_SYNC_SECRET;
const target=new URL("/functions/v1/carcare-ai-sync",base).href;
async function request(payload){
 const response=await fetch(target,{method:"POST",headers:{"content-type":"application/json","x-carcare-token":syncKey},body:JSON.stringify({source_key:"linkwise_carcare",...payload})});
 if(!response.ok)throw Error("CarCare VMDB sync "+response.status);
 return response.json();
}
