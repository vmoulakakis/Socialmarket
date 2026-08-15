import json
import os
import urllib.request

from product_agents import clamp, commission_score, discount_score, optional_score

CONFIG_GATEWAY = os.getenv(
    'PRODUCT_CONFIG_GATEWAY',
    'https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/product-config-gateway',
)


def load_runtime_config(v1):
    token = v1.oidc_token()
    req = urllib.request.Request(
        CONFIG_GATEWAY,
        headers={'authorization': 'Bearer ' + token, 'accept': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode())
    if not payload.get('ok') or not isinstance(payload.get('config'), dict):
        raise RuntimeError('runtime_product_config_unavailable')
    cfg = dict(payload['config'])
    cfg['_version'] = int(payload.get('version') or 0)
    cfg['_updated_at'] = payload.get('updated_at')
    cfg['_updated_by'] = payload.get('updated_by')
    return cfg


def save_run_profile(v1, phase, profile, status='completed'):
    token = v1.oidc_token()
    body = json.dumps(
        {'action': 'save_run_profile', 'phase': phase, 'status': status, 'profile': profile},
        ensure_ascii=False,
    ).encode()
    req = urllib.request.Request(
        CONFIG_GATEWAY,
        data=body,
        method='POST',
        headers={'authorization': 'Bearer ' + token, 'content-type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _num(cfg, key, fallback):
    try:
        return float(cfg.get(key, fallback))
    except Exception:
        return float(fallback)


def _int(cfg, key, fallback):
    try:
        return int(cfg.get(key, fallback))
    except Exception:
        return int(fallback)


def apply_runtime_config(v1, cfg):
    """Patch the V1 worker so database configuration is authoritative.

    Security invariants are not configurable here: unresolved merchants,
    dominant/blocked merchants, invalid price/currency/tracking/image, and
    non-VALIDATED AI results still cannot be persisted.
    """
    v1.MIN_COMMISSION = max(10.0, _num(cfg, 'min_expected_commission_eur', v1.MIN_COMMISSION))
    v1.MIN_MERCHANT_TRUST = max(0.0, min(100.0, _num(cfg, 'min_merchant_trust', v1.MIN_MERCHANT_TRUST)))
    v1.MIN_VALIDATED_PAIN_CLUSTERS = max(1, _int(cfg, 'min_validated_pain_clusters', v1.MIN_VALIDATED_PAIN_CLUSTERS))
    v1.MIN_AUDIT_OVERALL = max(0.0, min(100.0, _num(cfg, 'min_audit_overall', v1.MIN_AUDIT_OVERALL)))
    v1.MIN_PAIN_FIT = max(0.0, min(100.0, _num(cfg, 'min_pain_fit', v1.MIN_PAIN_FIT)))
    v1.MIN_PRODUCT_EVIDENCE = max(0.0, min(100.0, _num(cfg, 'min_product_evidence', v1.MIN_PRODUCT_EVIDENCE)))
    v1.AI_BATCH = max(1, min(12, _int(cfg, 'ai_batch', v1.AI_BATCH)))
    v1.AI_MAX_CANDIDATES = max(1, min(500, _int(cfg, 'ai_max_candidates', v1.AI_MAX_CANDIDATES)))
    v1.AI_OFFERS_PER_PRODUCT = max(1, min(3, _int(cfg, 'ai_offers_per_product', v1.AI_OFFERS_PER_PRODUCT)))
    v1.MAX_AI_BATCH_FAILURE_RATE = max(0.0, min(1.0, _num(cfg, 'max_ai_batch_failure_rate', v1.MAX_AI_BATCH_FAILURE_RATE)))

    pain_limit = max(1, min(20, _int(cfg, 'pain_rag_limit', 8)))
    theme_limit = max(0, min(10, _int(cfg, 'theme_rag_limit', 5)))
    min_ev = max(1, _int(cfg, 'min_pain_evidence_count', 1))
    min_src = max(1, _int(cfg, 'min_pain_source_diversity', 1))
    min_severity = max(0.0, min(100.0, _num(cfg, 'min_pain_severity', 0)))
    min_intent = max(0.0, min(100.0, _num(cfg, 'min_commercial_intent', 0)))
    min_demand = max(0.0, min(100.0, _num(cfg, 'min_greek_demand', 0)))
    max_comp = max(0.0, min(100.0, _num(cfg, 'max_competition', 100)))
    prelim = cfg.get('preliminary_weights') or {'commission': 45, 'merchant_whitespace': 35, 'demand': 20}
    weights = cfg.get('score_weights') or {
        'pain_gap_fit': 25, 'merchant_opportunity': 20, 'greek_demand': 15,
        'commission': 12, 'inverse_competition': 10, 'seasonal': 8,
        'merchant_trust': 5, 'discount': 3, 'evidence_confidence': 2,
    }

    def preliminary_score(p, merchant):
        commission = min(100, max(0, (p['expected_commission_eur'] - v1.MIN_COMMISSION) * 3 + 25))
        m = float(merchant.get('solution_whitespace_score') or 0)
        demand = float(merchant.get('demand_score') or 0)
        return round(
            commission * float(prelim.get('commission', 45)) / 100.0
            + m * float(prelim.get('merchant_whitespace', 35)) / 100.0
            + demand * float(prelim.get('demand', 20)) / 100.0,
            3,
        )

    def build_ai_item(p, context):
        merchant = p['merchant_context']
        pains = v1.select_pain_rag(p, context.get('pain_clusters', []), pain_limit)
        pains = [c for c in pains if (
            int(c.get('evidence_count') or 0) >= min_ev
            and int(c.get('source_diversity') or 0) >= min_src
            and c.get('pain_severity') is not None
            and float(c.get('pain_severity')) >= min_severity
            and c.get('commercial_intent') is not None
            and float(c.get('commercial_intent')) >= min_intent
            and c.get('demand_score') is not None
            and float(c.get('demand_score')) >= min_demand
            and c.get('competition_score') is not None
            and float(c.get('competition_score')) <= max_comp
        )]
        themes = v1.select_theme_rag(p, context.get('themes', []), theme_limit) if theme_limit else []
        return {
            'product': v1.compact_product_for_ai(p),
            'merchant': merchant,
            'pain_rag': [{k: x.get(k) for k in (
                'id', 'cluster_type', 'canonical_text', 'category', 'subcategory', 'evidence_count',
                'source_diversity', 'demand_score', 'competition_score', 'pain_severity',
                'commercial_intent', 'confidence', 'retrieval_score'
            )} for x in pains],
            'theme_rag': [{k: x.get(k) for k in (
                'id', 'slug', 'name', 'semantic_brief', 'active_from', 'peak_date', 'active_to',
                'retrieval_score', 'seasonal_curve_score'
            )} for x in themes],
            '_pains': pains, '_themes': themes, '_raw': p,
        }

    def final_opportunity_score(*, pain_gap_fit, merchant_opportunity, greek_demand, competition,
                                seasonal_theme, merchant_trust, expected_commission, discount,
                                evidence_confidence):
        values = {
            'pain_gap_fit_score': optional_score(pain_gap_fit),
            'merchant_opportunity_score': optional_score(merchant_opportunity),
            'greek_demand_score': optional_score(greek_demand),
            'competition_score': optional_score(competition),
            'seasonal_theme_score': optional_score(seasonal_theme),
            'merchant_trust_score': optional_score(merchant_trust),
            'commission_score': commission_score(expected_commission),
            'discount_score': discount_score(discount),
            'product_evidence_confidence': optional_score(evidence_confidence),
        }
        positive=lambda key:(values[key] if values[key] is not None else 0.0)
        inverse_comp=(100-values['competition_score']) if values['competition_score'] is not None else 0.0
        score = (
            positive('pain_gap_fit_score') * float(weights.get('pain_gap_fit', 25))
            + positive('merchant_opportunity_score') * float(weights.get('merchant_opportunity', 20))
            + positive('greek_demand_score') * float(weights.get('greek_demand', 15))
            + values['commission_score'] * float(weights.get('commission', 12))
            + inverse_comp * float(weights.get('inverse_competition', 10))
            + positive('seasonal_theme_score') * float(weights.get('seasonal', 8))
            + positive('merchant_trust_score') * float(weights.get('merchant_trust', 5))
            + values['discount_score'] * float(weights.get('discount', 3))
            + positive('product_evidence_confidence') * float(weights.get('evidence_confidence', 2))
        ) / 100.0
        missing=[k for k,v in values.items() if v is None]
        values['missing_components']=missing
        values['competition_inverse_bonus_withheld']=values['competition_score'] is None
        return round(clamp(score), 2), values

    v1.preliminary_score = preliminary_score
    v1.build_ai_item = build_ai_item
    v1.final_opportunity_score = final_opportunity_score

    thinking_mode = str(cfg.get('ai_thinking_mode') or 'auto')
    base_gateway = v1.gateway

    def configured_gateway(action, **payload):
        if action in ('enrich', 'audit'):
            payload['thinking'] = thinking_mode
        return base_gateway(action, **payload)

    v1.gateway = configured_gateway
    v1.RUNTIME_CONFIG = cfg
    return cfg
