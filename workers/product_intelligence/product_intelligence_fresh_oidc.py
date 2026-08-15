import json
import sys
from pathlib import Path

import product_intelligence_v1 as v1
from runtime_config import apply_runtime_config, load_runtime_config, save_run_profile


_original_gateway = v1.gateway


def fresh_gateway(action, **payload):
    """Force a fresh short-lived GitHub OIDC token for every gateway request."""
    v1._TOKEN = None
    return _original_gateway(action, **payload)


v1.gateway = fresh_gateway


if __name__ == '__main__':
    cfg = load_runtime_config(v1)
    apply_runtime_config(v1, cfg)
    print(json.dumps({
        'runtime_product_config': {
            'version': cfg.get('_version'),
            'profile_name': cfg.get('profile_name'),
            'updated_at': cfg.get('_updated_at'),
            'updated_by': cfg.get('_updated_by'),
        }
    }, ensure_ascii=False), flush=True)
    v1.main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
    profile_path = Path(v1.PROFILE_PATH)
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding='utf-8'))
        profile['runtime_config_version'] = cfg.get('_version')
        profile['runtime_profile_name'] = cfg.get('profile_name')
        save_run_profile(v1, 'B', profile)
