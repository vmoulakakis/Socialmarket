from __future__ import annotations

# v4.3 intentionally reuses the mature V4 collectors/audit pipeline but replaces
# the legacy merchant taxonomy decision before V4 imports the legacy module.
import merchant_intelligence_v3 as legacy
from semantic_taxonomy import resolve_merchant_taxonomy

_original_analyze = legacy.analyze


def semantic_identity_analyze(job):
    result = _original_analyze(job)
    tx = resolve_merchant_taxonomy(
        merchant_name=str(result.get('merchant_name') or job.get('canonical_name') or ''),
        site_title=str(result.get('site_title') or ''),
        site_description=str(result.get('site_description') or ''),
        anchors=(),  # fail closed: raw/ancillary navigation cannot classify the business in v4.3
        existing_category=None,
        existing_subcategory=None,
    )
    result['category'] = tx.category
    result['subcategory'] = tx.subcategory
    result['category_candidates'] = ([{
        'name': tx.category,
        'confidence': tx.confidence,
        'source': tx.source,
    }] if tx.category != 'Other' else [])
    result['subcategory_candidates'] = ([{
        'name': tx.subcategory,
        'confidence': tx.confidence,
        'source': tx.source,
    }] if tx.subcategory else [])

    # Category market truth is owned by the generic category worker.
    # Merchant research must not create a second demand/competition/pain truth.
    result['demand_score'] = None
    result['competition_score'] = None
    result['pain_gap_score'] = None
    result['metadata'] = {
        **(result.get('metadata') or {}),
        'taxonomy_resolution': tx.as_dict(),
        'taxonomy_owner': 'merchant_identity_only',
        'category_market_owner': 'semantic_category_pain_v2',
        'methodology': 'merchant_identity_semantic_v4.3',
    }
    unresolved = tx.category == 'Other' or tx.confidence < 0.72
    result['risk_flag'] = bool(result.get('risk_flag')) or unresolved
    if unresolved:
        result['risk_reason'] = 'merchant_taxonomy_unresolved_v4_3'
    result['semantic_text'] = ' | '.join(filter(None, [
        result.get('merchant_name'),
        tx.category if tx.category != 'Other' else None,
        tx.subcategory,
        result.get('site_title'),
        result.get('site_description'),
        f'merchant taxonomy confidence {tx.confidence:.2f}',
    ]))
    result['summary'] = (
        f"Merchant identity taxonomy: {tx.category}"
        + (f" / {tx.subcategory}" if tx.subcategory else '')
        + f"; confidence {tx.confidence:.0%}; source {tx.source}. "
        + "Category demand/competition/pain is intentionally delegated to semantic_category_pain_v2."
    )
    return result


legacy.analyze = semantic_identity_analyze

# Import after monkeypatch so both `import module` and `from module import analyze`
# styles inside V4 receive the v4.3 classifier.
import merchant_intelligence_v4 as v4  # noqa: E402

if hasattr(v4, 'legacy'):
    v4.legacy.analyze = semantic_identity_analyze


if __name__ == '__main__':
    v4.main()
