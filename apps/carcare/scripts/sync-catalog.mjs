import {normalizeFeed} from "../lib/catalog.mjs";
const source=process.env.LINKWISE_CARCARE_FEED_URL;
if(!source)throw Error("missing feed");
const response=await fetch(source,{signal:AbortSignal.timeout(70000)});
if(!response.ok)throw Error("invalid feed response");
const products=normalizeFeed(await response.json());
console.log("CarCare eligible imported candidate count",products.length);
