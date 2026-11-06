import assert from 'node:assert/strict';
import {
  BUYER_POLICY, auditOffer, normalize, searchTerms, selectForNeed, trustedAffiliateUrl,
} from '../lib/shopper-agent.mjs';

const NOW = new Date('2026-11-06T10:00:00.000Z');
const TRACKING_URL = 'https://go.linkwi.se/z/23-0/CD104/?lnkurl=https%3A%2F%2Fwww.laredoute.gr%2Fsofa';
const base = Object.freeze({
  source_product_id: 'sofa-100',
  product_name: 'Γωνιακός καναπές από ύφασμα',
  category_raw: 'Σπίτι · Καθιστικό',
  program_name: 'La Redoute',
  price_eur: 550,
  calculated_commission_eur: 55,
  tracking_url: TRACKING_URL,
  image_url: 'https://example.com/sofa.webp',
  is_active: true,
  in_stock: null,
  valid_to: null,
  last_seen_at: '2026-11-06T09:00:00Z',
});
const verified = Object.freeze({
  ...base,
  in_stock: true,
  valid_to: '2026-11-20T00:00:00Z',
  audit_status: 'VALIDATED',
  evidence_ids: ['evidence-source-1', 'audit-result-2'],
});

assert.equal(BUYER_POLICY.minimumCommissionEur, 10);
assert.equal(normalize('ΓΩΝΙΑΚΌΣ ΚΑΝΑΠΈΣ'), 'γωνιακος καναπες');
assert.ok(searchTerms('Θέλω γωνιακό καναπέ').length > 0);
assert.equal(trustedAffiliateUrl(TRACKING_URL), true);
assert.equal(trustedAffiliateUrl('javascript:alert(1)'), false);
assert.equal(trustedAffiliateUrl('https://go.linkwi.se.evil.example/'), false);
assert.equal(trustedAffiliateUrl('https://evil.example/?tracking=go.linkwi.se'), false);

assert.equal(auditOffer(base, NOW).status, 'NEEDS_VERIFICATION');
assert.ok(auditOffer(base, NOW).unanswered.includes('live_stock'));
assert.equal(auditOffer({ ...base, in_stock: false }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, valid_to: '2026-11-01T00:00:00Z' }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, calculated_commission_eur: 9.99 }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, tracking_url: 'https://shop.example/product' }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, image_url: 'ftp://example.com/photo.jpg' }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, program_name: '' }, NOW).status, 'BLOCKED');
assert.equal(auditOffer({ ...verified, program_id: '999' }, NOW).status, 'BLOCKED', 'network program ID conflict blocks offer');
assert.equal(auditOffer({ ...verified, program_id: '23' }, NOW).status, 'VERIFIED', 'matching network ID stays eligible');
assert.equal(auditOffer({ ...verified, tracking_url: 'https://go.linkwi.se/z/23-0/CD104/?lnkurl=' }, NOW).status, 'BLOCKED', 'malformed Linkwise route blocks offer');
assert.equal(auditOffer({ ...verified, last_seen_at: '2026-10-10T00:00:00Z' }, NOW).status, 'NEEDS_VERIFICATION');
assert.equal(auditOffer({ ...verified, audit_status: 'PENDING' }, NOW).status, 'NEEDS_VERIFICATION');
assert.equal(auditOffer(verified, NOW).status, 'VERIFIED');

const pendingResult = selectForNeed({ rows: [base], query: 'Γωνιακός καναπές', now: NOW });
assert.equal(pendingResult.status, 'WITHHELD');
assert.equal(pendingResult.verified.length, 0);
assert.equal(pendingResult.candidates.length, 1);
assert.equal(pendingResult.candidates[0].tracking_url, TRACKING_URL);

const validResult = selectForNeed({ rows: [verified], query: 'Γωνιακός καναπές', budget: 650, now: NOW });
assert.equal(validResult.status, 'VERIFIED_MATCHES');
assert.equal(validResult.verified.length, 1);
assert.equal(validResult.verified[0].tracking_url, TRACKING_URL);

const outOfBudget = selectForNeed({ rows: [verified], query: 'Γωνιακός καναπές', budget: 50, now: NOW });
assert.equal(outOfBudget.verified.length, 0);
assert.equal(outOfBudget.candidates.length, 0);

const noMatch = selectForNeed({ rows: [verified], query: 'ηλεκτρικη σκουπα', now: NOW });
assert.equal(noMatch.verified.length, 0);
const duplicate = selectForNeed({ rows: [verified, { ...verified, source_product_id: 'sofa-101' }], query: 'καναπές', now: NOW });
assert.equal(duplicate.verified.length, 1);
const noIntent = selectForNeed({ rows: [verified], query: 'θέλω ένα προϊόν', now: NOW });
assert.equal(noIntent.status, 'NEEDS_NEED');
const invalidBudget = selectForNeed({ rows: [verified], query: 'καναπές', budget: -4, now: NOW });
assert.equal(invalidBudget.status, 'INVALID_BUDGET');

const cheaper = { ...verified, source_product_id: 'sofa-cheaper', product_name: 'Γωνιακός καναπές οικονομικός', price_eur: 450, calculated_commission_eur: 10 };
const dearer = { ...verified, source_product_id: 'sofa-pricier', product_name: 'Γωνιακός καναπές πολυτελείας', price_eur: 800, calculated_commission_eur: 200 };
const ranked = selectForNeed({ rows: [dearer, cheaper], query: 'γωνιακός καναπές', now: NOW });
assert.equal(ranked.verified[0].id, 'sofa-cheaper', 'relevance and lower price rank before commission');

console.log('SHOPPER AGENT: 21 evidence, affiliate-integrity, intent, ranking and resilience checks passed.');
