import test from 'node:test';
import assert from 'node:assert/strict';
import {freePolicy,freeOpenRouterModels} from '../lib/free-llm-policy.mjs';
test('free provider routing is opt-in and disabled without a key',()=>{
 assert.deepEqual(freePolicy({GROQ_API_KEY:'dummy'}),{enabled:false,freeOnly:false,groq:false,openrouter:false});
});
test('Groq must have explicit free tier confirmation and key',()=>{
 assert.equal(freePolicy({FREE_LLM_FIRST_ENABLED:'true',GROQ_API_KEY:'dummy'}).groq,false);
 assert.equal(freePolicy({FREE_LLM_FIRST_ENABLED:'true',GROQ_API_KEY:'dummy',GROQ_FREE_TIER_CONFIRMED:'true'}).groq,true);
});
test('free-only defaults to on when free-first is enabled',()=>{
 assert.equal(freePolicy({FREE_LLM_FIRST_ENABLED:'true'}).freeOnly,true);
 assert.equal(freePolicy({FREE_LLM_FIRST_ENABLED:'true',FREE_LLM_ONLY:'false'}).freeOnly,false);
});
test('no paid OpenRouter fallback can leak into free-only mode',()=>{
 assert.deepEqual(freeOpenRouterModels('openai/gpt-4o'),['openrouter/free']);
 assert.deepEqual(freeOpenRouterModels('openrouter/free'),['openrouter/free']);
 assert.deepEqual(freeOpenRouterModels('meta-llama/test:free'),['meta-llama/test:free','openrouter/free']);
});
