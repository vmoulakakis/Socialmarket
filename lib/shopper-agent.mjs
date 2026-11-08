/**
 * SocialMarket Buyer Agent v1.
 * This is a bounded, deterministic evidence gate + retrieval stage.
 * It does not impersonate an LLM or claim that feed candidates are audited.
 * Only audited, fresh, stock-confirmed offers may become recommendations.
 */
import {decodeLinkwiseRoute} from './linkwise-identity.mjs';

export const BUYER_POLICY = Object.freeze({
  version: 'buyer-agent-v1',
  minimumCommissionEur: 10,
  maxReturned: 6,
  maxSourceRows: 100,
  maxEvidenceAgeHours: 48,
});

const STOP = new Set([
  'θελω','χρειαζομαι','για','ενα','μια','εναν','που','και','μου','στο','στη','στην',
  'να','με','απο','μεχρι','κατι','προιον','προιοντα','the','with','for','want',
  'buy','best','good','one','some','what','τι','ποιο','ποια','εως','ευρω',
]);
const VARIANTS = Object.freeze({
  καναπες: ['καναπε','σαλονι','καθιστικ'],
  στεγνωτηριο: ['στεγνωτηρ','στεγνωμα','στεγνω'],
  σκουπα: ['σκουπ','καθαρισ'],
  robot: ['ρομποτ','robot'],
});

export function normalize(text) {
  return String(text ?? '').toLocaleLowerCase('el-GR')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

export function searchTerms(input) {
  const terms = normalize(input).split(/\s+/).filter(x => x.length >= 3 && !STOP.has(x)).slice(0, 12);
  return [...new Set(terms.flatMap(term => {
    const matching = Object.entries(VARIANTS).find(([base, opts]) => term.startsWith(base.slice(0, 5)) || opts.some(v => term.startsWith(v.slice(0, 5))));
    return matching ? [...matching[1], term] : [term];
  }))];
}

export function trustedAffiliateUrl(value) {
  try {
    const u = new URL(String(value ?? ''));
    const h = u.hostname.toLowerCase();
    return u.protocol === 'https:' && !u.username && !u.password &&
      (h === 'go.linkwi.se' || h === 'affiliate.linkwi.se' ||
       h === 's.click.aliexpress.com' || h === 'a.aliexpress.com');
  } catch {
    return false;
  }
}

function validImage(value) {
  try { const u = new URL(value); return u.protocol === 'https:' && !!u.hostname; }
  catch { return false; }
}

function money(v) {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function auditOffer(row, now = new Date()) {
  const hardFailures = [];
  const unanswered = [];
  const price = money(row?.price_eur);
  const commission = Number(row?.calculated_commission_eur ?? row?.expected_commission_eur);
  if (!String(row?.source_product_id ?? '').trim() || !String(row?.product_name ?? row?.title ?? '').trim()) hardFailures.push('product_identity');
  if (!price) hardFailures.push('price');
  if (!Number.isFinite(commission) || commission < BUYER_POLICY.minimumCommissionEur) hardFailures.push('commission_floor');
  if (!trustedAffiliateUrl(row?.tracking_url ?? row?.promotion_url)) hardFailures.push('affiliate_tracking');
  const affiliate = row?.tracking_url ?? row?.promotion_url;
  if (trustedAffiliateUrl(affiliate)) {
    const h = new URL(affiliate).hostname.toLowerCase();
    if (h === 'go.linkwi.se' || h === 'affiliate.linkwi.se') {
      const network = decodeLinkwiseRoute(affiliate);
      if (!network) hardFailures.push('linkwise_route_unverified');
      if (network && row?.program_id != null && String(row.program_id) !== network.program_id)
        hardFailures.push('affiliate_program_identity_mismatch');
    }
  }
  if (!validImage(row?.image_url)) hardFailures.push('image');
  if (!String(row?.program_name ?? '').trim()) hardFailures.push('merchant_identity');
  if (row?.in_stock === false || row?.is_active === false) hardFailures.push('offer_inactive');
  if (row?.valid_to != null && (Number.isNaN(Date.parse(row.valid_to)) || new Date(row.valid_to) < now)) hardFailures.push('expired');
  if (row?.in_stock !== true) unanswered.push('live_stock');
  if (!row?.valid_to) unanswered.push('validity_window');
  const observed = row?.last_seen_at && Date.parse(row.last_seen_at);
  if (!observed || Number.isNaN(observed) || now.getTime() - observed > BUYER_POLICY.maxEvidenceAgeHours * 3600000 ||
      observed > now.getTime() + 3600000) unanswered.push('freshness');
  if (row?.audit_status !== 'VALIDATED' || !Array.isArray(row?.evidence_ids) || !row.evidence_ids.length) unanswered.push('skeptic_evidence');
  return {
    status: hardFailures.length ? 'BLOCKED' : unanswered.length ? 'NEEDS_VERIFICATION' : 'VERIFIED',
    hardFailures, unanswered,
  };
}

function relevance(row, terms) {
  const title = normalize(row.product_name ?? row.title);
  const category = normalize(row.category_raw ?? row.category);
  return terms.reduce((total, term) => {
    const key = term.length > 6 ? term.slice(0, 6) : term;
    return total + (title.includes(key) ? 4 : 0) + (category.includes(key) ? 2 : 0);
  }, 0);
}

export function selectForNeed({rows = [], query, budget = null, now = new Date()}) {
  const terms = searchTerms(query);
  const limit = budget === '' || budget == null ? null : Number(budget);
  if (!terms.length) return {policy: BUYER_POLICY.version, status: 'NEEDS_NEED', verified: [], candidates: [], diagnostic: 'Χρειάζεται συγκεκριμένο προϊόν ή πρόβλημα.'};
  if (limit !== null && (!Number.isFinite(limit) || limit <= 0 || limit > 100000)) return {policy: BUYER_POLICY.version, status: 'INVALID_BUDGET', verified: [], candidates: [], diagnostic: 'Μη έγκυρος προϋπολογισμός.'};
  const prepared = rows.slice(0, BUYER_POLICY.maxSourceRows).map(row => ({
    row, audit: auditOffer(row, now), relevance: relevance(row, terms),
  })).filter(x => x.relevance > 0 && (limit == null || Number(x.row.price_eur) <= limit));
  const unique = new Set();
  const eligible = prepared.filter(x => {
    const k = normalize(x.row.product_name ?? x.row.title).slice(0, 90) + ':' + normalize(x.row.program_name);
    if (unique.has(k)) return false;
    unique.add(k); return x.audit.status !== 'BLOCKED';
  });
  eligible.sort((a, b) => b.relevance - a.relevance ||
    Number(a.row.price_eur) - Number(b.row.price_eur));
  const format = ({row, audit, relevance: fit}) => ({
    id: String(row.source_product_id), title: String(row.product_name ?? row.title),
    merchant: String(row.program_name), category: String(row.category_raw ?? ''),
    image_url: row.image_url, price_eur: Number(row.price_eur),
    // Original source URL is preserved verbatim; no reconstructed deep links.
    tracking_url: row.tracking_url, relevance: fit, verification: audit.status,
    missing_checks: audit.unanswered,
  });
  const verified = eligible.filter(x => x.audit.status === 'VERIFIED').slice(0, BUYER_POLICY.maxReturned).map(format);
  const candidates = eligible.filter(x => x.audit.status === 'NEEDS_VERIFICATION').slice(0, BUYER_POLICY.maxReturned).map(format);
  return {
    policy: BUYER_POLICY.version, status: verified.length ? 'VERIFIED_MATCHES' : 'WITHHELD',
    verified, candidates, searched: Math.min(rows.length, BUYER_POLICY.maxSourceRows),
    diagnostic: verified.length
      ? 'Οι επιλογές πέρασαν τους τεκμηριωμένους ελέγχους.'
      : 'Δεν υπάρχουν επαληθευμένες προτάσεις. Οι πιθανές αντιστοιχίσεις απαιτούν ανεξάρτητο έλεγχο διαθεσιμότητας, ισχύος και evidence.',
    stages: [
      {name:'Intent mapper', status:'DONE'},
      {name:'Source & affiliate gate', status:'DONE'},
      {name:'Stock / freshness audit', status: verified.length ? 'DONE' : 'WITHHELD'},
      {name:'Skeptic & evidence', status: verified.length ? 'DONE' : 'WITHHELD'},
    ],
  };
}
