from __future__ import annotations

import threading

import consumer_evidence_v4 as consumer
from consumer_source_expansion_v43 import apply as apply_source_expansion
import consumer_direct_social_v44 as direct_social
from niche_product_prior_v45 import apply as apply_niche_product_prior
from niche_keyword_binding_v45 import apply as apply_niche_keyword_binding
from consumer_direct_greek_v46 import apply as apply_direct_greek

# V4.6 source policy:
# 1) crawlable Greek consumer communities,
# 2) direct YouTube public-comment acquisition for product-bound pain,
# 3) no Reddit JSON collection in this commercial pipeline,
# 4) concrete niche-product search intents,
# 5) exact product token/bigram taxonomy binding,
# 6) direct Greek forum discovery independent of SearX site-query coverage,
# 7) social/forum evidence is PAIN ONLY: no views/likes/followers as demand proof.
# Quality thresholds and cross-source skeptic gates remain unchanged.
apply_source_expansion()
direct_social.apply()
direct_social._reddit=lambda aliases,keywords,limit=24: []
apply_niche_product_prior()
apply_niche_keyword_binding()
apply_direct_greek()

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


if __name__=='__main__':
    v4.main()
