# OpenAPI Overlays

This directory contains [OpenAPI Overlay](https://spec.openapis.org/overlay/latest.html) files that describe distribution-specific API surface differences. Each file targets a specific OpenSearch distribution and lists the operations that are not available on that distribution.

## What are Overlays?

The [OpenAPI Overlay Specification](https://spec.openapis.org/overlay/latest.html) is an official companion spec from the OpenAPI Initiative. It defines a document format for information that augments an existing OpenAPI description yet remains separate from it. An Overlay contains an ordered list of actions (using RFC 9535 JSONPath targeting) that `update` or `remove` elements in a target OpenAPI document.

## Files

| File | Distribution | Description |
|------|-------------|-------------|
| `amazon-managed.overlay.yaml` | Amazon OpenSearch Service | Operations excluded from managed AOS domains |
| `amazon-serverless.overlay.yaml` | Amazon OpenSearch Serverless | Operations excluded from AOSS collections |

## Usage

### Producing a distribution-filtered spec

```bash
# Generate the merged spec first
npm run merge

# Apply an overlay to produce a filtered spec
npm run overlay:apply -- \
  --spec build/opensearch-openapi.yaml \
  --overlay overlays/amazon-managed.overlay.yaml \
  --output build/opensearch-openapi-amazon-managed.yaml
```

### Regenerating overlays from spec annotations

If `x-distributions-excluded` annotations change in the source spec:

```bash
npm run overlay:generate -- --source ./spec --output ./overlays
```

### Validating overlays match the extractor

This proves that applying an overlay produces the same result as the existing `OpenApiVersionExtractor` distribution filtering:

```bash
npm run overlay:validate -- --source ./spec --overlays ./overlays
```

## Adding Your Distribution's Overlay

If you maintain an OpenSearch distribution with a different API surface:

1. Create `overlays/<your-distribution>.overlay.yaml`
2. Use the existing files as a template
3. List the operations to remove using JSONPath targets:
   - `$.paths['/<path>']` removes an entire path (all methods)
   - `$.paths['/<path>'].<method>` removes a single method
4. Run `npm run overlay:validate` to confirm consistency
5. Submit a pull request

## Overlay Format

```yaml
overlay: 1.0.0
info:
  title: <Distribution Name> - API Surface Overlay
  version: YYYY.MM.DD
actions:
  - target: "$.paths['/_plugins/_security/authinfo']"
    remove: true
  - target: "$.paths['/_settings'].get"
    remove: true
```

## Background

This approach was proposed in [#1183](https://github.com/opensearch-project/opensearch-api-specification/issues/1183) to replace the inline `x-distributions-excluded` annotations with a standard, scalable mechanism. See the issue for full rationale and migration plan.
