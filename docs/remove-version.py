#!/usr/bin/env python3
"""
Drop info.version from the OpenSearch OpenAPI distribution docs.

info.version is the opensearch-api-specification repo's own spec version
(e.g. "0.3.0") -- meaningless as a doc badge. Scalar renders it as a "v0.3.0"
badge next to the title; dropping it removes the badge.

TODO(x-version-added rendering): per-operation "Minimum version" is intentionally
NOT rendered here. x-version-added is left untouched in the spec. The clean way
to surface it is a Scalar Specification-Extension plugin
(https://guides.scalar.com/scalar/scalar-api-references/plugins) that reads
x-version-added and renders a badge in the render layer -- keeping the data in
the structured field instead of injecting prose into descriptions. Deferred
because the standalone browser build (Scalar.createApiReference in index.html)
needs the plugin as a hosted ESM module (pluginUrls), i.e. a front-end build +
hosting step this POC does not have yet. AOSS has no x-version-added, so such a
plugin would naturally render nothing for it -- no per-distribution branching
needed.
"""
import json
import sys


def process_spec(spec):
    info = spec.get('info')
    if isinstance(info, dict):
        info.pop('version', None)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) < 2:
        print(f"Usage: {sys.argv[0]} <input.json> <output.json>")
        sys.exit(1)

    with open(args[0]) as f:
        spec = json.load(f)

    process_spec(spec)

    with open(args[1], 'w') as f:
        json.dump(spec, f)

    print(f"Dropped info.version; written: {args[1]}")
