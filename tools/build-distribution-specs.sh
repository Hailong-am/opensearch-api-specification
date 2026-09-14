#!/usr/bin/env bash
# Build distribution-specific OpenAPI specs from YAML + overlays.
# Source of truth: opensearch-openapi.yaml + overlay YAML files.
# No ad-hoc JSON manipulation allowed.
set -euo pipefail

SPEC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$SPEC_DIR/build"
OVERLAYS_DIR="$SPEC_DIR/overlays"
TOOLS_DIR="$SPEC_DIR/tools"
EXTENSIONS_DIR="${EXTENSIONS_DIR:-/local/home/ihailong}"

BASE_SPEC="$BUILD_DIR/opensearch-openapi.yaml"

echo "=== Building distribution specs from YAML + overlays ==="
echo "Base spec: $BASE_SPEC"

# --- OSS: base spec, no overlay ---
echo ""
echo "--- OSS ---"
cp "$BASE_SPEC" "$BUILD_DIR/opensearch-openapi-oss.yaml"

# --- AOS: remove overlay + UltraWarm extension ---
echo ""
echo "--- AOS ---"
echo "  Step 1: Apply remove overlay"
npx openapi-overlays-js \
  --openapi "$BASE_SPEC" \
  --overlay "$OVERLAYS_DIR/amazon-managed.overlay.yaml" \
  > "$BUILD_DIR/opensearch-openapi-aos.yaml"

echo "  Step 2: Apply UltraWarm extension overlay"
npx openapi-overlays-js \
  --openapi "$BUILD_DIR/opensearch-openapi-aos.yaml" \
  --overlay "$EXTENSIONS_DIR/aoss-ultrawarm-api.overlay.yaml" \
  > "$BUILD_DIR/opensearch-openapi-aos-warm.yaml"

echo "  Step 3: Apply Cold tier extension overlay"
npx openapi-overlays-js \
  --openapi "$BUILD_DIR/opensearch-openapi-aos-warm.yaml" \
  --overlay "$EXTENSIONS_DIR/aos-cold-api.overlay.yaml" \
  > "$BUILD_DIR/opensearch-openapi-aos-full.yaml"

# --- AOSS: remove overlay + snapshot extension ---
echo ""
echo "--- AOSS ---"
echo "  Step 1: Apply remove overlay"
npx openapi-overlays-js \
  --openapi "$BASE_SPEC" \
  --overlay "$OVERLAYS_DIR/amazon-serverless.overlay.yaml" \
  > "$BUILD_DIR/opensearch-openapi-aoss.yaml"

echo "  Step 2: Apply snapshot extension overlay"
npx openapi-overlays-js \
  --openapi "$BUILD_DIR/opensearch-openapi-aoss.yaml" \
  --overlay "$EXTENSIONS_DIR/aoss-snapshot-api-extensions.overlay.yaml" \
  > "$BUILD_DIR/opensearch-openapi-aoss-full.yaml"

# --- Convert YAML → JSON, strip deprecated, inject tags ---
echo ""
echo "=== Post-processing ==="
python3 -c "
import yaml, json
for name in ['opensearch-openapi-oss', 'opensearch-openapi-aos-full', 'opensearch-openapi-aoss-full']:
    with open(f'$BUILD_DIR/{name}.yaml') as f:
        data = yaml.safe_load(f)
    with open(f'$BUILD_DIR/{name}.json', 'w') as f:
        json.dump(data, f)
    print(f'  {name}: {len(data.get(\"paths\", {}))} paths → JSON')
"

echo ""
echo "--- Strip deprecated ---"
python3 "$TOOLS_DIR/strip-deprecated.py" "$BUILD_DIR/opensearch-openapi-oss.json" "$BUILD_DIR/opensearch-openapi-oss-clean.json"
python3 "$TOOLS_DIR/strip-deprecated.py" "$BUILD_DIR/opensearch-openapi-aos-full.json" "$BUILD_DIR/opensearch-openapi-aos-clean.json"
python3 "$TOOLS_DIR/strip-deprecated.py" "$BUILD_DIR/opensearch-openapi-aoss-full.json" "$BUILD_DIR/opensearch-openapi-aoss-clean.json"

echo ""
echo "--- Inject tags ---"
python3 "$TOOLS_DIR/inject-tags.py" "$BUILD_DIR/opensearch-openapi-oss-clean.json" "$BUILD_DIR/opensearch-openapi-oss-tagged.json"
python3 "$TOOLS_DIR/inject-tags.py" "$BUILD_DIR/opensearch-openapi-aos-clean.json" "$BUILD_DIR/opensearch-openapi-aos-tagged.json"
python3 "$TOOLS_DIR/inject-tags.py" "$BUILD_DIR/opensearch-openapi-aoss-clean.json" "$BUILD_DIR/opensearch-openapi-aoss-tagged.json"

echo ""
echo "=== Done ==="
echo "Output files:"
ls -lh "$BUILD_DIR"/*-tagged.json
