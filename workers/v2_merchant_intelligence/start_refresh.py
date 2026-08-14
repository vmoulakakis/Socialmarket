from __future__ import annotations

import argparse
import json
import os

from gateway import call


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merchant-id", default="")
    parser.add_argument("--reason", default=os.getenv("REFRESH_REASON", "scheduled_refresh"))
    args = parser.parse_args()
    result = call(
        "start_refresh",
        p_merchant_id=args.merchant_id.strip() or None,
        p_reason=args.reason,
    ) or {}
    print(json.dumps(result))
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"run_id={result.get('run_id','')}\n")
            fh.write(f"queued_merchants={result.get('queued_merchants',0)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
