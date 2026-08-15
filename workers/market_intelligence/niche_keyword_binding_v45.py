from __future__ import annotations

"""Product-token binding for Greece niche pain V4.5.

The base taxonomy intentionally uses broad semantic labels. Niche consumer pain
often names a concrete object (mini UPS, router, robot vacuum filter, suitcase
wheel) without repeating the broad category label. This patch expands the
keyword binder with safe tokens/bigrams derived only from the curated niche
query terms, so exact product pain can pass taxonomy binding without relaxing
first-person, purchase/use, cross-domain or skeptic gates.
"""

import re

import category_pain_intelligence as base
from niche_product_prior_v45 import NICHE_TERMS
from semantic_taxonomy import fold

_ORIGINAL_KEYWORD_SET=base.keyword_set
_APPLIED=False
_STOP={
    'για','που','και','την','τον','στο','στη','στην','απο','χωρις','with','for','the','and',
    'home','smart','setup','product','school','σπιτι','σχολειο','γραφειο','ταξιδι',
}


def _dedup(values):
    out=[];seen=set()
    for value in values:
        value=fold(value)
        if len(value)<4 or value in seen:continue
        seen.add(value);out.append(value)
    return out


def keyword_set(category,subcategory,query_terms):
    base_keys=list(_ORIGINAL_KEYWORD_SET(category,subcategory,query_terms))
    niche=list(NICHE_TERMS.get((str(category or ''),str(subcategory or '')),()))
    extra=[]
    for phrase in niche[:3]:
        f=fold(phrase)
        toks=[x for x in re.findall(r'[a-z0-9α-ω]+',f) if len(x)>=4 and x not in _STOP]
        extra.extend(toks)
        extra.extend(' '.join(toks[i:i+2]) for i in range(max(0,len(toks)-1)))
        # Preserve high-information full phrase as another exact binder.
        if len(f)>=4:extra.append(f)
    return _dedup([*extra,*base_keys])[:120]


def apply():
    global _APPLIED
    if _APPLIED:return
    base.keyword_set=keyword_set
    _APPLIED=True
