import sys

import product_intelligence_v1 as v1


_original_gateway = v1.gateway


def fresh_gateway(action, **payload):
    """Force a fresh short-lived GitHub OIDC token for every gateway request."""
    v1._TOKEN = None
    return _original_gateway(action, **payload)


v1.gateway = fresh_gateway


if __name__ == '__main__':
    v1.main(sys.argv[1] if len(sys.argv) > 1 else v1.SOURCE_FEED)
