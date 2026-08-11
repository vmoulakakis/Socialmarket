import run_pipeline_v7 as v7
import run_pipeline as core
from competitor_v2 import strict_candidates, strict_get_or_create

_original_get_or_create = core.get_or_create_competitor
core.competitor_candidates = lambda results, products, agent_runtime, run_id: strict_candidates(
    core, results, products, agent_runtime, run_id
)
core.get_or_create_competitor = lambda candidate: strict_get_or_create(
    core, _original_get_or_create, candidate
)

if __name__ == '__main__':
    core.main()
