/**
 * MyAgenticTeam free-tier policy adapter for SocialMarket.
 * One canonical router remains lib/model-router.js.
 * This module contains only deterministic eligibility rules and no secrets.
 */
export function freePolicy(env={}){
 const enabled=env.FREE_LLM_FIRST_ENABLED==='true';
 return {
  enabled,
  freeOnly:enabled&&env.FREE_LLM_ONLY!=='false',
  groq:enabled&&Boolean(env.GROQ_API_KEY)&&env.GROQ_FREE_TIER_CONFIRMED==='true',
  openrouter:enabled&&Boolean(env.OPENROUTER_API_KEY)
 };
}
export function freeOpenRouterModels(configured){
 const model=typeof configured==='string'?configured.trim():'';
 const names=[...(model.endsWith(':free')||model==='openrouter/free'?[model]:[]),'openrouter/free'];
 return [...new Set(names)];
}
