from __future__ import annotations

import threading

import consumer_evidence_v4 as consumer
from consumer_source_expansion_v43 import apply as apply_source_expansion
import consumer_direct_social_v44 as direct_social
from niche_product_prior_v45 import apply as apply_niche_product_prior

# V4.5 source policy:
# 1) expand crawlable Greek consumer communities,
# 2) keep direct YouTube public-comment acquisition for product-bound pain,
# 3) disable the Reddit JSON collector for this commercial research pipeline,
# 4) prepend concrete niche-product intents and enforce social=pain-only.
# None of these changes relax the V4 skeptic/validation thresholds.
apply_source_expansion()
direct_social.apply()
direct_social._reddit=lambda aliases,keywords,limit=24: []
apply_niche_product_prior()

# libxml/lxml-backed extraction can abort the interpreter when several
# Trafilatura parses run concurrently in the same GitHub runner process. Keep
# network I/O concurrent, but serialize the native parser critical section.
_EXTRACT_LOCK=threading.Lock()
_ORIGINAL_EXTRACT=consumer.trafilatura.extract


def _serial_extract(*args,**kwargs):
    with _EXTRACT_LOCK:
        return _ORIGINAL_EXTRACT(*args,**kwargs)


consumer.trafilatura.extract=_serial_extract

import category_pain_intelligence_v4 as v4  # noqa: E402  (patch before import/use)


if __name__=='__main__':
    v4.main()
