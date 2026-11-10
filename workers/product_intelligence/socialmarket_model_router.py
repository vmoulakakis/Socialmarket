"""SocialMarket model policy: deterministic first, bounded local models next, paid AI last.

Pure deterministic routing; the router never generates a merchant claim or uses an
external model. Embedder / Qwen runtimes must pass Greek, Greeklish, and factuality
quality gates before being enabled. Charges are never incurred by routing.
"""
from __future__ import annotations
from dataclasses import dataclass

E5 = "intfloat/multilingual-e5-small"
LOCAL = "Qwen/Qwen3-0.6B"
REMOTE = "existing_budgeted_socialmarket-ai"
VALID_TASKS = {
    "identity", "commission", "feed_delta", "vector_embedding", "semantic_matching",
    "category_tagging", "product_extraction", "greek_market_research",
    "contradiction_review", "compliance_review", "portfolio_strategy",
}

@dataclass(frozen=True)
class ModelDecision:
    tier: str
    model: str | None
    reason: str
    charges_remote_tokens: bool
    requires_approval: bool = False


def select_model(*, task: str, confidence: float = 0,
                 source_count: int = 0, independent_verified_sources: int = 0,
                 contradictory_evidence: bool = False, local_model_validated: bool = False,
                 hard_policy_question: bool = False) -> ModelDecision:
    if task not in VALID_TASKS:
        return ModelDecision("blocked", None, "unsupported_task", False)
    if not 0 <= confidence <= 1 or min(source_count,independent_verified_sources) < 0:
        return ModelDecision("blocked", None, "invalid_quality_metrics", False)
    if independent_verified_sources > source_count:
        return ModelDecision("blocked", None, "verified_count_exceeds_sources", False)
    if task in ("identity","commission","feed_delta"):
        # No model can validate missing affiliate approvals or financial terms.
        return ModelDecision("sql_rules",None,"source_and_exact_contract_required",False)
    if task in ("vector_embedding","semantic_matching"):
        return ModelDecision("cpu_embedding",E5,"deterministic_multilingual_retrieval",False)
    if task in ("category_tagging","product_extraction"):
        if confidence>=0.85:
            return ModelDecision("sql_rules",None,"high_confidence_structured_fields",False)
        if local_model_validated:
            return ModelDecision("local_small",LOCAL,"cheap_semantic_tagging_with_qa",False)
        return ModelDecision("evidence_queue",None,"local_model_not_benchmarked",False)
    if independent_verified_sources < 2:
        return ModelDecision("evidence_queue",None,"insufficient_independent_verified_sources",False)
    if hard_policy_question:
        return ModelDecision("manual_review",None,"high_impact_affiliate_compliance",False,True)
    if not contradictory_evidence and confidence>=0.85:
        return ModelDecision("sql_graph",None,"verified_evidence_sufficient",False)
    if task in ("greek_market_research","contradiction_review","compliance_review","portfolio_strategy"):
        return ModelDecision("remote_bounded",REMOTE,"complex_ambiguous_evidence",True)
    return ModelDecision("evidence_queue",None,"unresolved",False)
