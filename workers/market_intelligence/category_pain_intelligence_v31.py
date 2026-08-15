from __future__ import annotations

import category_pain_intelligence as base
from authoritative_context_v2 import authoritative_context_rows

# Runtime override only. All canonical scoring, audit gates and persistence remain
# owned by the tested base collector/evidence gateway.
base.authoritative_context_rows=authoritative_context_rows

if __name__=='__main__':
    base.main()
