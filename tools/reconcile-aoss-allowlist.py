#!/usr/bin/env python3
"""
Reconcile the AOSS supported-operations ALLOWLIST (AWS official doc:
serverless-genref.html) against the OSS base OpenAPI spec, and emit the
KEEP / REMOVE decision for every OSS operation.

Model (Option 2): the AWS doc is authoritative for what AOSS *allows*;
a small set of empirically-verified operations are unioned in because the
doc omits them but real collections accept them.

Output: a diff report (stdout) + a generated remove-overlay
(overlays/amazon-serverless-allowlist.overlay.yaml) that, applied to the OSS
base, leaves exactly the reconciled AOSS operation set.

Match granularity is per-(path) : an OSS path is KEPT if ANY method on it is
allowed AND we keep the whole path entry (overlay removes are path-level in the
existing overlay). Where the doc allows only some methods on a path we note it
but still keep the path (method-level pruning is a separate, optional pass).
"""
import json
import re
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent
BASE = SPEC_DIR / "build" / "opensearch-openapi.json"

HTTP_METHODS = ("get", "put", "post", "delete", "head", "patch")

# A placeholder in the doc ( <index>, <id>, <alias>, <target>, ... ) matches
# any single OSS path segment that is a {curly} placeholder OR a concrete
# segment. We normalise by replacing every {xxx} in the OSS path with a
# sentinel, then matching against doc patterns whose placeholders are the
# same sentinel.
PH = "\x01"  # sentinel for "one placeholder segment"


def normalize(path: str) -> str:
    """Replace every {param} segment with the placeholder sentinel."""
    return re.sub(r"\{[^}]+\}", PH, path)


# ---------------------------------------------------------------------------
# The ALLOWLIST, transcribed verbatim from serverless-genref.html.
# Each entry: (methods, doc_path). doc_path uses <x> for placeholders.
# <x> -> matches exactly one placeholder segment (PH).
# A doc_path may correspond to several OSS paths (index-scoped + global).
# ---------------------------------------------------------------------------
ALLOW = [
    # aoss:CreateIndex
    ("PUT", "/<index>"),
    # aoss:DescribeIndex
    ("GET", "/<index>"),
    ("GET", "/<index>/_mapping"),
    ("GET", "/<index>/_mappings"),
    ("GET", "/<index>/_settings"),
    ("GET", "/<index>/_settings/<setting>"),
    ("GET", "/_cat/indices"),
    ("GET", "/_cat/indices/<index>"),
    ("GET", "/_mapping"),
    ("GET", "/_mappings"),
    ("GET", "/_resolve/index/<index>"),
    ("HEAD", "/<index>"),
    # aoss:WriteDocument
    ("DELETE", "/<index>/_doc/<id>"),
    ("POST", "/<index>/_bulk"),
    ("POST", "/<index>/_create/<id>"),
    ("POST", "/<index>/_doc"),
    ("POST", "/<index>/_update/<id>"),
    ("POST", "/_bulk"),
    ("PUT", "/<index>/_create/<id>"),
    ("PUT", "/<index>/_doc/<id>"),
    # aoss:ReadDocument
    ("GET", "/<index>/_analyze"),
    ("GET", "/<index>/_doc/<id>"),
    ("GET", "/<index>/_explain/<id>"),
    ("GET", "/<index>/_mget"),
    ("GET", "/<index>/_source/<id>"),
    ("GET", "/<index>/_count"),
    ("GET", "/<index>/_field_caps"),
    ("GET", "/<index>/_msearch"),
    ("GET", "/<index>/_rank_eval"),
    ("GET", "/<index>/_search"),
    ("GET", "/<index>/_validate/query"),
    ("GET", "/_analyze"),
    ("GET", "/_field_caps"),
    ("GET", "/_mget"),
    ("GET", "/_search"),
    ("GET", "/_search/point_in_time/_all"),
    ("HEAD", "/<index>/_doc/<id>"),
    ("HEAD", "/<index>/_source/<id>"),
    ("POST", "/_plugins/_sql"),
    ("POST", "/_plugins/_ppl"),
    ("POST", "/_plugins/_sql/_explain"),
    ("POST", "/_plugins/_ppl/_explain"),
    ("POST", "/_plugins/_ppl/close"),  # doc: _ppl/_close -> OSS path is /close
    ("POST", "/<index>/_analyze"),
    ("POST", "/_search/point_in_time"),
    ("POST", "/<index>/_explain/<id>"),
    ("POST", "/<index>/_count"),
    ("POST", "/<index>/_field_caps"),
    ("POST", "/<index>/_rank_eval"),
    ("POST", "/<index>/_search"),
    ("POST", "/_analyze"),
    ("POST", "/_field_caps"),
    ("POST", "/_search"),
    ("DELETE", "/_search/point_in_time/_all"),
    ("DELETE", "/_search/point_in_time"),
    # aoss:DeleteIndex
    ("DELETE", "/<target>"),  # matches /<index>
    # aoss:UpdateIndex
    ("POST", "/_mapping"),
    ("POST", "/<index>/_mapping"),
    ("POST", "/<index>/_mappings"),
    ("POST", "/<index>/_settings"),
    ("POST", "/_settings"),
    ("PUT", "/_mapping"),
    ("PUT", "/<index>/_mapping"),
    ("PUT", "/<index>/_mappings"),
    ("PUT", "/<index>/_settings"),
    ("PUT", "/_settings"),
    # aoss:CreateCollectionItems
    ("POST", "/_aliases"),
    ("POST", "/_plugins/_flow_framework/workflow"),
    ("POST", "/_plugins/_flow_framework/workflow/<id>/_provision"),
    ("PUT", "/_ingest/pipeline/<id>"),
    ("PUT", "/_search/pipeline/<id>"),
    # aoss:DescribeCollectionItems
    ("GET", "/<index>/_alias/<alias>"),
    ("GET", "/_alias"),
    ("GET", "/_alias/<alias>"),
    ("GET", "/_cat/aliases"),
    ("GET", "/_cat/templates"),
    ("GET", "/_cat/templates/<name>"),
    ("GET", "/_component_template"),
    ("GET", "/_component_template/<name>"),
    ("GET", "/_index_template"),
    ("GET", "/_index_template/<name>"),
    ("GET", "/_ingest/pipeline/<id>"),
    ("GET", "/_ingest/pipeline/_simulate"),
    ("GET", "/_plugins/_flow_framework/workflow/<id>"),
    ("GET", "/_plugins/_flow_framework/workflow/_search"),
    ("GET", "/_plugins/_flow_framework/workflow/<id>/_status"),
    ("GET", "/_plugins/_flow_framework/workflow/state/_search"),
    ("GET", "/_plugins/_flow_framework/workflow/_steps"),
    ("GET", "/_plugins/_flow_framework/workflow/_step"),
    ("GET", "/_search/pipeline/<id>"),
    ("HEAD", "/_alias/<alias>"),
    ("HEAD", "/_component_template/<name>"),
    ("HEAD", "/_index_template/<name>"),
    ("HEAD", "/<index>/_alias/<alias>"),
    ("POST", "/_ingest/pipeline/_simulate"),
    ("POST", "/_plugins/_flow_framework/workflow/_search"),
    ("POST", "/_plugins/_flow_framework/workflow/state/_search"),
    # aoss:UpdateCollectionItems
    ("POST", "/<index>/_alias/<alias>"),
    ("POST", "/<index>/_aliases/<alias>"),
    ("POST", "/_component_template/<name>"),
    ("POST", "/_index_template/<name>"),
    ("POST", "/_plugins/_flow_framework/workflow/<id>/_deprovision"),
    ("PUT", "/<index>/_alias/<alias>"),
    ("PUT", "/<index>/_aliases/<alias>"),
    ("PUT", "/_component_template/<name>"),
    ("PUT", "/_index_template/<name>"),
    ("PUT", "/_plugins/_flow_framework/workflow/<id>"),
    # aoss:DeleteCollectionItems
    ("DELETE", "/<index>/_alias/<alias>"),
    ("DELETE", "/_component_template/<name>"),
    ("DELETE", "/_index_template/<name>"),
    ("DELETE", "/<index>/_aliases/<alias>"),
    ("DELETE", "/_search/pipeline/<id>"),
    ("DELETE", "/_ingest/pipeline/<id>"),
    ("DELETE", "/_plugins/_flow_framework/workflow/<id>"),
    # aoss:DescribeMLResource
    ("GET", "/_plugins/_ml/models/<model_id>"),
    ("GET", "/_plugins/_ml/models/_search"),
    ("GET", "/_plugins/_ml/model_groups/<model_group_id>"),
    ("GET", "/_plugins/_ml/model_groups/_search"),
    ("GET", "/_plugins/_ml/connectors/<connector_id>"),
    ("GET", "/_plugins/_ml/connectors/_search"),
    ("GET", "/_plugins/_ml/profile/tasks/<task_id>"),
    ("POST", "/_plugins/_ml/models/_search"),
    ("POST", "/_plugins/_ml/model_groups/_search"),
    ("POST", "/_plugins/_ml/connectors/_search"),
    # aoss:CreateMLResource
    ("POST", "/_plugins/_ml/models/_register"),
    ("POST", "/_plugins/_ml/model_groups/_register"),
    ("POST", "/_plugins/_ml/connectors/_create"),
    # aoss:UpdateMLResource
    ("PUT", "/_plugins/_ml/models/<model_id>"),
    ("POST", "/_plugins/_ml/models/<model_id>/_deploy"),
    ("POST", "/_plugins/_ml/models/<model_id>/_undeploy"),
    ("PUT", "/_plugins/_ml/model_groups/<model_group_id>"),
    ("PUT", "/_plugins/_ml/connectors/<connector_id>"),
    # aoss:DeleteMLResource
    ("DELETE", "/_plugins/_ml/models/<model_id>"),
    ("DELETE", "/_plugins/_ml/model_groups/<model_group_id>"),
    ("DELETE", "/_plugins/_ml/connectors/<connector_id>"),
    ("DELETE", "/_plugins/_ml/tasks/<task_id>"),
    # aoss:ExecuteMLResource
    ("POST", "/_plugins/_ml/models/<model_id>/_predict"),
    # aoss:CreateAgent
    ("POST", "/_plugins/_ml/agents/_register"),
    # aoss:DescribeAgent
    ("GET", "/_plugins/_ml/agents/<agent_id>"),
    # aoss:UpdateAgent
    ("PUT", "/_plugins/_ml/agents/<agent_id>"),
    # aoss:DeleteAgent
    ("DELETE", "/_plugins/_ml/agents/<agent_id>"),
    # aoss:InvokeAgent
    ("POST", "/_plugins/_ml/agents/<agent_id>/_execute"),
    # aoss:SearchAgents
    ("POST", "/_plugins/_ml/agents/_search"),
]

# ---------------------------------------------------------------------------
# EMPIRICAL KEEPS - operations the doc omits but real AOSS collections accept.
# Sourced from episodic memory / probe results. These are KEPT even if the
# allowlist does not name them. Path-level.
# ---------------------------------------------------------------------------
EMPIRICAL_KEEP_PATHS = {
    # scroll works on AOSS SEARCH collections (returns _scroll_id) - probe 2026
    "/_search/scroll",
    "/_search/scroll/{scroll_id}",
    # Snapshot APIs - AOSS ships snapshot extensions (create_repo, restore, get)
    "/_snapshot/{repository}",
    "/_snapshot/{repository}/{snapshot}",
    "/_snapshot/{repository}/{snapshot}/_restore",
    # PIT index-scoped variant (doc lists global PIT; index PIT is the same feature)
    "/{index}/_search/point_in_time",
    # msearch global (doc lists index msearch + GET _search; msearch body form)
    "/_msearch",
}


def build_matchers():
    matchers = []
    for method, docpath in ALLOW:
        norm = docpath.replace("<setting>", PH)
        norm = re.sub(r"<[^>]+>", PH, norm)
        matchers.append((method.lower(), norm))
    return matchers


def main():
    spec = json.loads(BASE.read_text())
    paths = spec["paths"]
    matchers = build_matchers()
    matcher_set = set(matchers)

    kept_paths = {}
    removed_paths = {}
    kept_ops = 0
    removed_ops = 0
    empirical_used = set()

    for path, item in sorted(paths.items()):
        norm = normalize(path)
        methods = [m for m in item if m in HTTP_METHODS]
        allowed_methods = []
        for m in methods:
            if (m, norm) in matcher_set:
                allowed_methods.append(m)
        keep = bool(allowed_methods)
        reason = "allowlist"
        if not keep and path in EMPIRICAL_KEEP_PATHS:
            keep = True
            reason = "empirical"
            empirical_used.add(path)
            allowed_methods = methods
        if keep:
            kept_paths[path] = (allowed_methods, methods, reason)
            kept_ops += len(methods)
        else:
            removed_paths[path] = methods
            removed_ops += len(methods)

    # Report
    print("=" * 70)
    print("AOSS ALLOWLIST RECONCILIATION (Option 2: doc ∪ empirical)")
    print("=" * 70)
    print(f"OSS base:        {len(paths)} paths")
    print(f"KEEP:            {len(kept_paths)} paths ({kept_ops} ops)")
    print(f"REMOVE:          {len(removed_paths)} paths ({removed_ops} ops)")
    print(f"empirical keeps: {sorted(empirical_used)}")
    unused_emp = EMPIRICAL_KEEP_PATHS - empirical_used - set(kept_paths)
    print(f"empirical paths NOT in OSS base (check names): {sorted(unused_emp)}")

    # Partial-method keeps (path kept but doc allows only some methods)
    print("\n--- Paths kept where doc allows a SUBSET of methods ---")
    for path, (allowed, methods, reason) in sorted(kept_paths.items()):
        if reason == "allowlist" and set(allowed) != set(methods):
            extra = sorted(set(methods) - set(allowed))
            print(f"  {path}: keep {sorted(allowed)}, doc-silent on {extra}")

    if "--write-overlay" in sys.argv:
        out = SPEC_DIR / "overlays" / "amazon-serverless-allowlist.overlay.yaml"
        lines = [
            "overlay: 1.0.0",
            "info:",
            "  title: Amazon OpenSearch Serverless - Allowlist-derived removal overlay",
            "  version: 2026.09.03",
            "  description: >-",
            "    Generated by tools/reconcile-aoss-allowlist.py from the AWS official",
            "    supported-operations doc (serverless-genref.html), reconciled with",
            "    empirically-verified operations (scroll, snapshot extensions, PIT).",
            "    Removes every OSS operation NOT in the reconciled AOSS allowlist.",
            "actions:",
        ]
        for path in sorted(removed_paths):
            esc = path.replace("'", "\\'")
            lines.append(f"  - target: $.paths['{esc}']")
            lines.append("    remove: true")
        out.write_text("\n".join(lines) + "\n")
        print(f"\nWrote overlay: {out}  ({len(removed_paths)} remove actions)")

    # Dump full remove list for audit
    if "--list-removed" in sys.argv:
        print("\n--- REMOVED paths ---")
        for path in sorted(removed_paths):
            print(f"  {path}")
    if "--list-kept" in sys.argv:
        print("\n--- KEPT paths ---")
        for path in sorted(kept_paths):
            print(f"  {path}  [{kept_paths[path][2]}]")


if __name__ == "__main__":
    main()
