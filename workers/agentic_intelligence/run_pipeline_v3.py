import run_pipeline as core
from research_v2 import discover_market_queries, relevant_searx

_original_searx = core.searx
core.discover_market_queries = discover_market_queries
core.searx = lambda query, limit=8: relevant_searx(_original_searx, query, limit)

if __name__ == '__main__':
    core.main()
