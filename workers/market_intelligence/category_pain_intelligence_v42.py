from __future__ import annotations

import threading

import consumer_evidence_v4 as consumer
from consumer_source_expansion_v43 import apply as apply_source_expansion
from consumer_direct_social_v44 import apply as apply_direct_social

# Expand discovery/source families, then add independent direct public-social
# acquisition. Neither layer changes the V4 skeptic/validation thresholds.
apply_source_expansion()
apply_direct_social()

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
