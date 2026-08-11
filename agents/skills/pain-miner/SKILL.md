---
name: pain-miner
description: Turn independent customer evidence into normalized, scored pain candidates without inventing market problems.
---
# Pain Miner

Extract pains rule-first, cluster with local embeddings/fuzzy similarity, and use a free/local semantic agent only for ambiguous normalization or concise labels. A model may group or label supplied evidence; it may not create missing evidence.

Pain score is deterministic. Require source diversity and retain contradictions. Status gates are database-enforced: weak signal <50; validated requires score >=70 and at least 3 independent sources; strong validated requires score >=85, at least 3 independent sources and at least 8 evidence items.

Store every evidence link so the user can inspect why a pain exists.
