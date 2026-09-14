"""Production Night Brain entrypoint with canonical VMDB Merchant 360 admission."""
from __future__ import annotations

import sys

import affiliate_night_brain_entrypoint as prod
from vmdb_merchant_admission import gated_stage_feed


# Replace only the product staging boundary. Everything downstream keeps the mature
# Night Brain scoring/creative stack, but its merchant universe is now the canonical
# VMDB diversified eligible view and therefore fail-closed.
prod.v1.stage_feed = lambda feed, context: gated_stage_feed(prod.stage_feed, feed, context)


if __name__ == "__main__":
    prod.night.main(sys.argv[1] if len(sys.argv) > 1 else prod.v1.SOURCE_FEED)
