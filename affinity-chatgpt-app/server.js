import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';
import http from 'node:http';

const AFFINITY = {
  market: 'Greece', currency: 'EUR', minCommissionEur: 20,
  priceAdvantagePct: 30, northStar: 'Revenue per Unique Visitor (RPV)',
  gates: ['Greek demand','pain/desire','Greece fulfillment','verified commission > €20','merchant/product quality','Greek exact/equivalent search','economic advantage','warranty/protection','logistics','claim integrity']
};

const server = new McpServer({ name: 'AFFINITY', version: '0.1.0' });

server.registerTool('affinity_policy', {
  title: 'AFFINITY Policy',
  description: 'Use this when you need the canonical AFFINITY rules, gates, thresholds, and decision policy for Greece-first affiliate intelligence.',
  inputSchema: {},
  annotations: { readOnlyHint: true, openWorldHint: false }
}, async () => ({ content:[{type:'text',text:JSON.stringify(AFFINITY,null,2)}], structuredContent: AFFINITY }));

server.registerTool('evaluate_candidate', {
  title: 'Evaluate Affiliate Candidate',
  description: 'Use this when evaluating a product against AFFINITY hard gates before building or promoting it.',
  inputSchema: {
    product: z.string(), price_eur: z.number().positive(), expected_commission_eur: z.number().nonnegative(),
    ships_to_greece: z.boolean(), greek_demand_verified: z.boolean(), greek_equivalent_price_eur: z.number().positive().optional(),
    affiliate_tracking_verified: z.boolean().default(false), warranty_verified: z.boolean().default(false), merchant_quality_verified: z.boolean().default(false)
  },
  annotations: { readOnlyHint: true, openWorldHint: false }
}, async (x) => {
  const gap = x.greek_equivalent_price_eur ? ((x.greek_equivalent_price_eur-x.price_eur)/x.greek_equivalent_price_eur)*100 : null;
  const blockers=[];
  if(!x.greek_demand_verified) blockers.push('Greek demand not verified');
  if(!x.ships_to_greece) blockers.push('Greece fulfillment failed');
  if(x.expected_commission_eur<=20) blockers.push('Verified expected commission must exceed €20');
  if(gap!==null && gap<30) blockers.push('Total-cost advantage below 30% versus meaningful Greek equivalent');
  if(!x.warranty_verified) blockers.push('Warranty/returns not verified');
  if(!x.merchant_quality_verified) blockers.push('Merchant/product quality not verified');
  if(!x.affiliate_tracking_verified) blockers.push('Affiliate tracking URL not verified');
  const decision = blockers.length ? 'HOLD' : 'BUILD_PRIORITIZE';
  const result={...x,real_price_gap_pct:gap===null?null:Number(gap.toFixed(2)),decision,blockers,north_star:AFFINITY.northStar};
  return { content:[{type:'text',text:JSON.stringify(result,null,2)}], structuredContent: result };
});

server.registerTool('plan_research', {
  title: 'Plan AFFINITY Research',
  description: 'Use this when a user asks AFFINITY to find or validate an affiliate opportunity; returns the mandatory evidence-first research plan.',
  inputSchema: { query:z.string(), market:z.string().default('Greece'), min_price_eur:z.number().nonnegative().optional() },
  annotations:{readOnlyHint:true,openWorldHint:true}
}, async (x)=>{
  const plan={query:x.query,market:x.market,min_price_eur:x.min_price_eur??null,steps:['Query authenticated affiliate/product sources','Verify Greece delivery and current price','Verify exact product-level affiliate eligibility and commission','Validate Greek demand','Search exact model, aliases, OEM/rebrands and functional equivalents in Greek market','Compare total solution cost','Audit seller, warranty, returns and logistics','Classify claims and evidence freshness','Score only after hard gates','Return BUILD_PRIORITIZE / BUILD_TEST / HOLD / REJECT','Generate and validate affiliate deep link before conversion traffic','Let surviving product determine funnel architecture']};
  return {content:[{type:'text',text:JSON.stringify(plan,null,2)}],structuredContent:plan};
});

const httpServer=http.createServer(async(req,res)=>{
  if(req.url!=='/mcp'){res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({name:'AFFINITY',status:'ok',mcp:'/mcp'}));}
  const transport=new StreamableHTTPServerTransport({sessionIdGenerator:undefined});
  res.on('close',()=>transport.close());
  await server.connect(transport);
  await transport.handleRequest(req,res);
});
const port=Number(process.env.PORT||3000);
httpServer.listen(port,()=>console.log(`AFFINITY MCP listening on ${port}`));
