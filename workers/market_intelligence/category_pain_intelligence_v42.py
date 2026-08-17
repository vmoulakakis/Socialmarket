from __future__ import annotations

import os
import threading

import consumer_evidence_v4 as consumer
from consumer_source_expansion_v43 import apply as apply_source_expansion
import consumer_direct_social_v44 as direct_social
from niche_product_prior_v45 import apply as apply_niche_product_prior
from niche_keyword_binding_v45 import apply as apply_niche_keyword_binding
from consumer_direct_greek_v46 import apply as apply_direct_greek
from consumer_searx_forum_v47 import apply as apply_searx_forum
from consumer_forum_seed_crawl_v48 import apply as apply_forum_seed_crawl

# V4.8 source policy:
# 1) crawlable Greek consumer communities,
# 2) direct YouTube public-comment acquisition for product-bound pain,
# 3) no Reddit JSON collection in this commercial pipeline,
# 4) concrete niche-product search intents,
# 5) exact product token/bigram taxonomy binding,
# 6) legacy DDG/Bing direct-Greek discovery retained for diagnostic parity,
# 7) domain-bound SearXNG discovery retained as a secondary discovery path,
# 8) verified public forum index seeds are crawled shallowly, same-domain only,
# 9) search snippets/index text remain discovery-only; actual fetched topic text is mandatory,
# 10) no login/CAPTCHA/403/anti-bot bypass,
# 11) social/forum evidence is PAIN ONLY: no views/likes/followers as demand proof.
# Quality thresholds and cross-source skeptic gates remain unchanged.
apply_source_expansion()
direct_social.apply()
direct_social._reddit=lambda aliases,keywords,limit=24: []
apply_niche_product_prior()
apply_niche_keyword_binding()
apply_direct_greek()
apply_searx_forum()
apply_forum_seed_crawl()

# libxml/lxml-backed extraction can abort the interpreter when several
# Trafilatura parses run concurrently in the same GitHub runner process. Keep
# network I/O concurrent, but serialize the native parser critical section.
_EXTRACT_LOCK=threading.Lock()
_ORIGINAL_EXTRACT=consumer.trafilatura.extract


def _serial_extract(*args,**kwargs):
    with _EXTRACT_LOCK:
        return _ORIGINAL_EXTRACT(*args,**kwargs)


consumer.trafilatura.extract=_serial_extract

import category_pain_intelligence_v4 as v4  # noqa: E402


# Compatibility seam for the Autopilot AI Task Router. Production defaults to
# local_router on the canonical workflow after benchmark qualification.
if os.getenv('CATEGORY_PAIN_AI_ROUTE','legacy_gateway').strip().lower() == 'local_router':
    from category_pain_local_audit import audit_items  # noqa: E402

    _ORIGINAL_GATEWAY=v4.base.gateway

    def _routed_gateway(action,**payload):
        if action == 'audit_batch':
            return {'ok':True,**audit_items(list(payload.get('items') or []))}
        return _ORIGINAL_GATEWAY(action,**payload)

    v4.base.gateway=_routed_gateway


if __name__=='__main__':
    v4.main()
