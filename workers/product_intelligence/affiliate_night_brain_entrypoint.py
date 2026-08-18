"""Production entrypoint for Affiliate Night Brain with bounded business gates.

Keeps the core Night Brain orchestration single and stable while replacing only the
bulk-gate and frontier hooks with the audited v1.1 business policy.
"""
from __future__ import annotations

import sys

import affiliate_night_brain as night
import product_intelligence_v1 as v1
from night_brain_gate_tools import build_frontier_with_business_gates, stage_feed


_CORE_BUILD_FRONTIER = night.build_frontier


def _frontier(db, context, decision_index, policy):
    return build_frontier_with_business_gates(_CORE_BUILD_FRONTIER, db, context, decision_index, policy)


# Production refinements. Runtime configuration still patches scoring/context helpers
# before execution; these two hooks are intentionally narrow and auditable.
v1.stage_feed = stage_feed
night.build_frontier = _frontier


if __name__ == '__main__':
    night.main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
