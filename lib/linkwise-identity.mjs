/**
 * Non-mutating Linkwise source reconciliation.
 * A program ID in a link identifies a route, NOT merchant approval or live
 * commission. Never promote based on guessed names or old commission rows.
 */
const CLIENT = 'CD104';
const TRACK_HOSTS = new Set(['go.linkwi.se', 'affiliate.linkwi.se']);

export function decodeLinkwiseRoute(trackingUrl) {
  try {
    const url = new URL(String(trackingUrl ?? ''));
    if (url.protocol !== 'https:' || !TRACK_HOSTS.has(url.hostname.toLowerCase()) || url.username || url.password) return null;
    const match = /^\/z\/([1-9]\d*)-(\d+)\/(CD\d+)\/?$/.exec(url.pathname);
    if (!match || match[3] !== CLIENT) return null;
    const encoded = url.searchParams.get('lnkurl');
    if (!encoded) return null;
    const destination = new URL(encoded);
    if (!['http:', 'https:'].includes(destination.protocol) || destination.username || destination.password || !destination.hostname) return null;
    return {
      program_id: match[1],
      publisher_id: match[3],
      destination_host: destination.hostname.toLowerCase().replace(/^www\./, ''),
      destination_protocol: destination.protocol,
    };
  } catch {
    return null;
  }
}
const toText = value => String(value ?? '').trim();
function sameDomain(a,b) {
  const x = toText(a).toLowerCase().replace(/^www\./, '').replace(/\.$/,'');
  const y = toText(b).toLowerCase().replace(/^www\./, '').replace(/\.$/,'');
  return !!x && !!y && (x === y || x.endsWith('.' + y));
}

/** Program rows must come from authoritative verified Linkwise data. */
export function reconcileLinkwiseOffer(offer, { programs = [], merchants = [], now = new Date() } = {}) {
  const route = decodeLinkwiseRoute(offer?.tracking_url);
  const reasons = [];
  if (!route) reasons.push('INVALID_NETWORK_ROUTE');
  if (route && toText(offer?.program_id) && toText(offer.program_id) !== 'unknown' && toText(offer.program_id) !== route.program_id)
    reasons.push('PROGRAM_ID_CONFLICT');
  if (offer?.in_stock === false) reasons.push('OUT_OF_STOCK');
  if (offer?.is_active === false) reasons.push('INACTIVE');
  if (offer?.valid_to && (!Number.isFinite(Date.parse(offer.valid_to)) || Date.parse(offer.valid_to) < now.getTime()))
    reasons.push('EXPIRED');

  const program = route ? programs.find(p => toText(p.linkwise_program_id ?? p.program_id) === route.program_id) : null;
  const merchant = route && program
    ? merchants.find(m => sameDomain(route.destination_host, m.canonical_domain) &&
       toText(m.merchant_name).toLowerCase() === toText(program.program_name).toLowerCase()) ?? null
    : null;

  if (!program) reasons.push('PROGRAM_NOT_IN_AUTHORITY');
  if (!merchant) reasons.push('MERCHANT_NOT_CANONICALLY_VERIFIED');
  if (program && program.program_approved !== true) reasons.push('PROGRAM_APPROVAL_UNKNOWN');
  if (merchant && (merchant.active !== true || merchant.program_approved !== true || merchant.tracking_verified !== true))
    reasons.push('MERCHANT_APPROVAL_UNKNOWN');
  const price = Number(offer?.price_eur);
  if (!Number.isFinite(price) || price <= 0) reasons.push('INVALID_PRICE');
  const flat = Number(program?.flat_commission_min_eur);
  const pct = Number(program?.percent_commission_min);
  const minFlat = program?.flat_commission_min_eur != null && Number.isFinite(flat) && flat > 0 ? flat : null;
  const minPct = program?.percent_commission_min != null && Number.isFinite(pct) && pct > 0 ? price * pct / 100 : null;
  const minima = [minFlat, minPct].filter(x => x != null);
  const minimumCommission = minima.length ? Math.min(...minima) : null;
  if (minimumCommission === null) reasons.push('COMMISSION_TERMS_UNKNOWN');
  else if (minimumCommission < 10) reasons.push('COMMISSION_UNDER_10');
  if (offer?.in_stock !== true) reasons.push('STOCK_NOT_CONFIRMED');
  const last = Date.parse(offer?.last_seen_at || '');
  if (!Number.isFinite(last) || now.getTime() - last > 48 * 3600000 || last > now.getTime() + 3600000)
    reasons.push('FEED_NOT_FRESH');
  return {
    status: reasons.length === 0 ? 'READY_FOR_INDEPENDENT_SKEPTIC' : 'NEEDS_RECONCILIATION',
    route_program_id: route?.program_id ?? null,
    merchant_id: merchant?.id ?? null,
    merchant_name: merchant?.merchant_name ?? null,
    expected_min_commission_eur: minimumCommission === null ? null : Math.round(minimumCommission * 100) / 100,
    reasons: [...new Set(reasons)],
  };
}

export function summariseReconciliation(rows, catalogs = {}) {
  const counts = {};
  const byProgram = {};
  for (const row of rows) {
    const item = reconcileLinkwiseOffer(row, catalogs);
    const key = item.route_program_id || 'invalid';
    byProgram[key] ||= { total: 0, ready_for_skeptic: 0 };
    byProgram[key].total++;
    if (item.status === 'READY_FOR_INDEPENDENT_SKEPTIC') byProgram[key].ready_for_skeptic++;
    for (const reason of item.reasons) counts[reason] = (counts[reason] || 0) + 1;
  }
  return { processed: rows.length, byProgram, reason_counts: counts, writes: 0, source_links_replaced: 0 };
}
