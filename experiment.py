"""MatRouter release-bound EvidenceBundle-first three-case paper experiment."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import time
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".runtime-cache" / "matplotlib"))
REPOSITORY_ROOT = ROOT
IDENTITY_PATH = ROOT / "product-identity.release.json"
CASES = ("mos2-band-gap", "lifepo4-stability", "bi2se3-topology")
PROTOCOL_VERSION = "matrouter.paper-three-case-protocol"
FINAL_RELEASE_BINDING = {
    "package_version": "0.10.2",
    "public_VERSION": "0.10.2",
    "release_tag": "v0.10.2",
}
FORMAL_CAPTURE_ENABLED = True
FORMAL_CAPTURE_PAUSE_REASON = (
    "Formal capture is disabled for the configured release identity."
)
COMMON_RESEARCH_QUESTIONS = {
    "RQ1": "Within the declared catalog, configuration, scope, and budgets, does one all-qualified aggregate attempt every capability-matched route and preserve each typed outcome and RecordCompleteness?",
    "RQ2": "What material-data landscape does that same authoritative aggregate Bundle support—sources, data categories, scientific contexts, specialist data, completeness, and explicit gaps—and how does that landscape guide the next research step?",
    "RQ3": "Can an Agent use the aggregate to locate preregistered exact source-bound records and artifacts for explicit lightweight methods, while making unsupported heavy calculations an explicit external handoff rather than a proxy result?",
}
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
CASE_RESULTS = RESULTS / "cases"
ARTIFACTS = RESULTS / "artifacts"

OPTIMADE_WILDCARD_EXCLUSIONS = {
    "unavailable": ["alexandria", "cmr", "mpod"],
    "out_of_scope": ["psdi"],
    "duplicate": ["atomgpt"],
    "native_adapter_duplicates": [
        "mp",
        "mpds",
        "oqmd",
        "aflow",
        "jarvis",
        "alexandria",
        "nmd",
        "cod",
        "tcod",
    ],
}
THERMO_TYPE = "GGA_GGA+U_R2SCAN"
ON_HULL_TOLERANCE_EV_PER_ATOM = 1e-6
PAPER_ELIGIBILITY_SEMANTICS = (
    "Protocol eligibility under the frozen case gates; not validation of scientific truth, "
    "accuracy, significance, or external reproducibility."
)
QUALIFIED_ROUTE_COUNT_SEMANTICS = (
    "Counts refer to qualified execution routes, not statistically independent evidence units. "
    "MaterialsGalaxy summary is one provider-level execution route; child dataset names on "
    "returned records are exact provenance, not additional execution outcomes."
)
STAGE_1_SCOPE = (
    "RQ1 and RQ2 share one aggregate_source_records call and one authoritative discovery Bundle. "
    "MatRouter performs bounded parallel cross-source execution over all parsed qualified routes "
    "with ordered_parallel_map (at most eight workers), preserves stable route-order aggregation, "
    "and keeps pagination within each source sequential. The evaluation declares only "
    "all_qualified plus exhaust_upstream; MatRouter owns the effective records, pages, elapsed-time, "
    "normalized-byte, and Bundle-closure engineering ceilings. Capacity stops remain explicit in "
    "RecordCompleteness. Outcomes and warnings are embedded in executions and do not consume the "
    "scientific-item budget. All ready qualified "
    "routes are attempted, but not every upstream record is claimed retrieved. RQ1 projects route "
    "execution and closure; RQ2 projects source contributions and material-data context from the "
    "same executions and source-record items."
)
SHARED_DISCOVERY_POLICY = {
    "acquisition": "exactly_one_all_qualified_aggregate_source_records_call_per_case",
    "source_scope": "all_qualified",
    "record_scope": "exhaust_upstream",
    "engineering_ceiling_authority": "matrouter_product_defaults",
    "evaluation_ceiling_overrides": [],
    "aggregate_fanout": "product_ordered_parallel_map_max_8_with_stable_route_order",
    "per_source_pagination": "sequential",
    "additional_source_record_acquisitions": 0,
    "analysis_views": ["RQ1", "RQ2"],
    "authoritative_bundle_count": 1,
}
SHARED_DISCOVERY_SCOPE = (
    "Each case has exactly one source-record acquisition: one all-qualified, exhaust-upstream "
    "aggregate_source_records call. The evaluation supplies no records, pages, elapsed-time, "
    "normalized-byte, or Bundle-closure ceiling overrides; the installed MatRouter release owns "
    "those engineering defaults and the capture records their effective values. RQ1 and RQ2 are "
    "two deterministic views of this single authority ledger; no second discovery or "
    "selected-source supplement is permitted."
)

EXPECTED_TOOLS = (
    "begin_evidence_run",
    "list_source_files",
    "download_source_file",
    "inspect_evidence_capabilities",
    "create_evidence_requirement",
    "route_evidence_requirements",
    "aggregate_source_records",
    "execute_evidence_route",
    "assemble_evidence_bundle",
    "match_structures",
    "compute_phase_diagrams",
    "render_band_structure",
    "render_density_of_states",
)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(value: object) -> bytes:
    return canonical_json(value).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def experiment_id(identity: dict[str, Any]) -> str:
    return f"matrouter-v{identity['package_version']}-three-scientific-cases"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _new_full_run_id(package_version: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"matrouter-{package_version}-full-{stamp}-{uuid4().hex[:12]}"


def _portable_site_package_path(path: Path) -> str:
    resolved = path.resolve()
    if "site-packages" not in resolved.parts:
        raise ValueError("installed MatRouter path is not a site-packages distribution")
    index = resolved.parts.index("site-packages")
    return "/".join(resolved.parts[index:])


def _runtime_distribution_audit() -> dict[str, Any]:
    import matrouter

    installed_distribution = distribution("matrouter")
    distribution_root = Path(installed_distribution.locate_file("matrouter")).resolve()
    imported_root = Path(matrouter.__file__).resolve().parent
    product_source_pythonpath_entries = 0
    for raw_entry in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if not raw_entry:
            continue
        candidate = (Path(raw_entry).resolve() / "matrouter").resolve()
        if (candidate / "__init__.py").is_file() and candidate != distribution_root:
            product_source_pythonpath_entries += 1
    if product_source_pythonpath_entries:
        raise ValueError("PYTHONPATH must not inject MatRouter product source")
    direct_url_absent = installed_distribution.read_text("direct_url.json") is None
    paths_match = imported_root == distribution_root
    if not direct_url_absent or not paths_match:
        raise ValueError(
            "runtime MatRouter must be the installed registry distribution"
        )
    return {
        "distribution_name": installed_distribution.metadata["Name"],
        "distribution_version": installed_distribution.metadata["Version"],
        "public_VERSION": matrouter.VERSION,
        "metadata_version": installed_distribution.metadata["Metadata-Version"],
        "requires_python": installed_distribution.metadata["Requires-Python"],
        "summary": installed_distribution.metadata["Summary"],
        "imported_package_path": _portable_site_package_path(imported_root),
        "distribution_package_path": _portable_site_package_path(distribution_root),
        "imported_path_matches_distribution": paths_match,
        "direct_url_json_absent": direct_url_absent,
        "product_source_pythonpath_entries": product_source_pythonpath_entries,
        "registry_distribution_verified": True,
    }


def wire(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: wire(child) for key, child in value.items()}
    if isinstance(value, list):
        return tuple(wire(child) for child in value)
    return value


def load_private_environment() -> None:
    """Load only MatRouter settings without displaying secret values."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = config_home / "matrouter" / "env"
    if not path.is_file():
        return
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = shlex.split(line, comments=True, posix=True)
        if tokens and tokens[0] == "export":
            tokens = tokens[1:]
        if len(tokens) != 1 or "=" not in tokens[0]:
            raise ValueError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = tokens[0].split("=", 1)
        if not key.startswith("MATROUTER_"):
            continue
        os.environ.setdefault(key, value)


async def _mcp_tool_names() -> list[str]:
    from fastmcp import Client
    from matrouter.router import MatRouter
    from matrouter.server import create_server

    with patch("matrouter.server.create_router", return_value=MatRouter([])):
        server = create_server()
    async with Client(server) as client:
        return [tool.name for tool in await client.list_tools()]


def _registry_distribution_matches_import(
    installed_distribution: Any, imported_root: Path
) -> bool:
    installed_root = Path(installed_distribution.locate_file("matrouter")).resolve()
    return (
        imported_root.resolve() == installed_root
        and installed_distribution.read_text("direct_url.json") is None
    )


def verify_release_identity() -> dict[str, Any]:
    import matrouter
    from matrouter.evidence_contracts import (
        EvidenceBundle,
        EvidenceRequirement,
        ExecutionWarningPayload,
        RouteCandidate,
        RouteExecution,
        ScientificArtifactItem,
        SourceOutcomePayload,
        StructureItem,
        record_result,
    )
    from matrouter.retrieval import RecordCompleteness

    identity = load_json(IDENTITY_PATH)
    installed_distribution = distribution("matrouter")
    if version("matrouter") != identity["package_version"]:
        raise ValueError("installed MatRouter version mismatch")
    if matrouter.VERSION != identity["public_VERSION"]:
        raise ValueError("installed MatRouter public VERSION mismatch")
    metadata = identity["distribution_metadata"]
    if installed_distribution.metadata["Name"] != metadata["name"]:
        raise ValueError("installed distribution name mismatch")
    if installed_distribution.metadata["Version"] != metadata["version"]:
        raise ValueError("installed distribution metadata version mismatch")
    if (
        installed_distribution.metadata["Metadata-Version"]
        != metadata["metadata_version"]
    ):
        raise ValueError("installed distribution metadata version mismatch")
    if (
        installed_distribution.metadata["Requires-Python"]
        != metadata["requires_python"]
    ):
        raise ValueError("installed distribution Python requirement mismatch")
    if installed_distribution.metadata["Summary"] != metadata["summary"]:
        raise ValueError("installed distribution summary mismatch")
    imported_root = Path(matrouter.__file__).resolve().parent
    if not _registry_distribution_matches_import(installed_distribution, imported_root):
        raise ValueError(
            "evaluation must import the installed PyPI package, not local source"
        )
    retired_identity_fields = {
        "schema_version",
        "payload_schema_id",
        "contract_version",
    }
    for model in (
        EvidenceRequirement,
        EvidenceBundle,
        StructureItem,
        ScientificArtifactItem,
        RouteExecution,
        SourceOutcomePayload,
        ExecutionWarningPayload,
    ):
        if retired_identity_fields & model.model_fields.keys():
            raise ValueError(
                f"{model.__name__} retains a retired product identity field"
            )
    route_contract = identity["route_contract"]
    if "aggregate_sources" not in RouteCandidate.model_fields:
        raise ValueError("installed RouteCandidate lacks required aggregate_sources")
    bundle_contract = identity["evidence_bundle_contract"]
    if set(EvidenceBundle.model_fields) != {
        "matrouter_version",
        "bundle_id",
        "requirements",
        "routes",
        bundle_contract["scientific_items_field"],
        bundle_contract["execution_ledger_field"],
    }:
        raise ValueError(
            "installed EvidenceBundle fields differ from the 0.10.2 contract"
        )
    if set(RouteExecution.model_fields) != {
        "attempt_id",
        "route_id",
        "input_attempt_id",
        "input_item_id",
        "output_item_ids",
        "outcome",
        "warnings",
        "started_at",
        "completed_at",
    }:
        raise ValueError(
            "installed RouteExecution fields differ from the release contract"
        )
    if "execution_status" not in SourceOutcomePayload.model_fields:
        raise ValueError("installed SourceOutcomePayload lacks execution_status")
    if (
        record_result(
            SourceOutcomePayload(
                execution_status="succeeded",
                reason_code="identity_probe",
                record_completeness=RecordCompleteness(
                    state="complete",
                    returned_count=0,
                    upstream_total=0,
                    pages_fetched=1,
                    exhaustion_evidence="identity_probe",
                ),
            ),
            operation="search_materials",
        )
        != "empty"
    ):
        raise ValueError("installed derived record_result contract mismatch")
    from matrouter.evidence_contracts import (
        MAX_BUNDLE_CANONICAL_BYTES,
        MAX_BUNDLE_EVIDENCE_ITEMS,
        MAX_BUNDLE_EXECUTIONS,
        MAX_BUNDLE_SOURCE_RECORDS,
    )

    capacity_checks = {
        "max_source_records": MAX_BUNDLE_SOURCE_RECORDS,
        "max_evidence_items": MAX_BUNDLE_EVIDENCE_ITEMS,
        "max_executions": MAX_BUNDLE_EXECUTIONS,
        "max_bundle_canonical_bytes": MAX_BUNDLE_CANONICAL_BYTES,
    }
    if any(bundle_contract[key] != value for key, value in capacity_checks.items()):
        raise ValueError("installed EvidenceBundle capacity profile mismatch")
    from matrouter._parallel import MAX_PARALLEL_SOURCE_CALLS

    if (
        MAX_PARALLEL_SOURCE_CALLS
        != route_contract["aggregate_max_parallel_source_workers"]
    ):
        raise ValueError("installed aggregate parallel-worker bound mismatch")
    names = asyncio.run(_mcp_tool_names())
    if names != identity["core_profile"]["tools"] or tuple(names) != EXPECTED_TOOLS:
        raise ValueError("installed MCP tools/list differs from the release identity")
    if len(names) != identity["core_profile"]["tool_count"]:
        raise ValueError("installed MCP tool count mismatch")
    for dependency, expected_version in identity["runtime_dependencies"].items():
        if version(dependency) != expected_version:
            raise ValueError(f"installed {dependency} version mismatch")
    return identity


def case_spec(case_name: str) -> dict[str, Any]:
    spec = load_json(ROOT / "cases" / f"{case_name}.json")
    if spec.get("case_name") != case_name:
        raise ValueError(f"{case_name}: case identity mismatch")
    if spec.get("schema_version") != "matrouter.paper-case-spec/13":
        raise ValueError(f"{case_name}: case schema mismatch")
    if spec.get("research_question_ids") != list(COMMON_RESEARCH_QUESTIONS):
        raise ValueError(f"{case_name}: common research-question binding mismatch")
    landscape = spec.get("material_landscape")
    if not isinstance(landscape, dict):
        raise TypeError(f"{case_name}: material-landscape declaration is missing")
    for field in (
        "cross_source_union_adds",
        "researcher_use",
        "external_handoff",
    ):
        if not landscape.get(field):
            raise ValueError(f"{case_name}: material-landscape {field} is missing")
    for claim in landscape["cross_source_union_adds"]:
        if not claim.get("statement") or not claim.get("supporting_contributions"):
            raise ValueError(f"{case_name}: source-contribution claim is invalid")
        if any(
            not support.get("source") or not support.get("data_categories")
            for support in claim["supporting_contributions"]
        ):
            raise ValueError(f"{case_name}: source-contribution support is invalid")
    applicability = spec.get("rq3_method_applicability")
    if not isinstance(applicability, dict) or applicability.get("status") not in {
        "applicable",
        "not_applicable",
    }:
        raise ValueError(f"{case_name}: RQ3 method applicability is missing")
    if not applicability.get("reason"):
        raise ValueError(f"{case_name}: RQ3 applicability reason is missing")
    expected_methods = applicability.get("expected_method_names")
    if not isinstance(expected_methods, list) or (
        applicability["status"] == "applicable" and not expected_methods
    ):
        raise ValueError(f"{case_name}: RQ3 expected methods are invalid")
    if applicability["status"] == "not_applicable" and expected_methods:
        raise ValueError(f"{case_name}: non-applicable RQ3 cannot expect a method")
    expected_stage_1 = {
        "evidence_kind": "source_record",
        "source_scope": "all_qualified",
        "record_scope": "exhaust_upstream",
        "engineering_ceiling_authority": "matrouter_product_defaults",
        "evaluation_ceiling_overrides": [],
    }
    if spec.get("stage_1") != expected_stage_1:
        raise ValueError(f"{case_name}: Stage 1 differs from the common frozen budget")
    if spec.get("shared_discovery_policy") != SHARED_DISCOVERY_POLICY:
        raise ValueError(f"{case_name}: shared discovery policy mismatch")
    targets = spec.get("stage_2_targets")
    if not isinstance(targets, list):
        raise TypeError(f"{case_name}: Stage 2 targets must be an explicit list")
    target_keys: set[tuple[str, str]] = set()
    for target in targets:
        key = (target.get("qualified_source_route"), target.get("source_id"))
        if not all(isinstance(value, str) and value for value in key):
            raise ValueError(f"{case_name}: Stage 2 target identity is incomplete")
        if key in target_keys:
            raise ValueError(f"{case_name}: duplicate Stage 2 exact target {key}")
        target_keys.add(key)
        if not target.get("scientific_role") or not target.get("selection_timing"):
            raise ValueError(f"{case_name}: Stage 2 target rationale is incomplete")
        routes = target.get("enrichment_routes")
        if not isinstance(routes, list) or len(
            {(row.get("evidence_kind"), row.get("operation")) for row in routes}
        ) != len(routes):
            raise ValueError(f"{case_name}: Stage 2 target routes are invalid")
        if any(
            not row.get("evidence_kind") or not row.get("operation") for row in routes
        ):
            raise ValueError(f"{case_name}: Stage 2 target route is incomplete")
    return spec


def _stage2_target_audit(raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    aggregate_run = next(
        row for row in raw["runs"] if row["run_role"] == "primary_aggregate"
    )
    aggregate_records = _bundle_items(
        aggregate_run["canonical_bundle"], "source_record"
    )
    aggregate_identities = [_record_from_item(item) for item in aggregate_records]
    aggregate_discovered = {
        (record.get("source"), record.get("source_id"))
        for record in aggregate_identities
    }
    target_runs = [row for row in raw["runs"] if row["run_role"] == "target_followup"]
    primary_acquisitions = {
        acquisition["acquisition_id"]: acquisition
        for acquisition in aggregate_run["acquisitions"]
    }
    additional_discovery_acquisitions = [
        acquisition
        for run in target_runs
        for acquisition in run["acquisitions"]
        if acquisition["route"]["operation"] == "search_materials"
    ]
    requirements = {
        row["requirement_id"]: row
        for run in target_runs
        for row in run["requirements"]
        if row["evidence_kind"] != "source_record"
    }
    routes = [row for run in target_runs for row in run["routes"]]
    acquisitions = [row for run in target_runs for row in run["acquisitions"]]
    target_rows: list[dict[str, Any]] = []
    for target in spec["stage_2_targets"]:
        source = target["qualified_source_route"]
        source_id = target["source_id"]
        found_in_aggregate = (source, source_id) in aggregate_discovered
        route_rows: list[dict[str, Any]] = []
        for expected in target["enrichment_routes"]:
            matching_acquisitions = [
                row
                for row in acquisitions
                if row["requirement"]["evidence_kind"] == expected["evidence_kind"]
                and row["route"]["operation"] == expected["operation"]
                and (row.get("input_record_ref") or {}).get("source") == source
                and (row.get("input_record_ref") or {}).get("source_id") == source_id
            ]
            matching_ids = {
                row["requirement"]["requirement_id"] for row in matching_acquisitions
            }
            matching_requirements = [
                row
                for row in requirements.values()
                if row["requirement_id"] in matching_ids
                and row["operational_constraints"].get("sources") == [source]
            ]
            matching_routes = [
                row
                for row in routes
                if row["requirement_id"] in matching_ids
                and row["operation"] == expected["operation"]
            ]
            bound_to_primary = [
                row
                for row in matching_acquisitions
                if row.get("input_acquisition_id") in primary_acquisitions
                and row.get("input_record_ref")
                in primary_acquisitions[row["input_acquisition_id"]].get(
                    "record_refs", []
                )
            ]
            route_rows.append(
                {
                    **expected,
                    "requirement_count": len(matching_requirements),
                    "ready_route_count": sum(
                        _route_is_ready(row) for row in matching_routes
                    ),
                    "executed_count": len(matching_acquisitions),
                    "bound_to_primary_discovery_count": len(bound_to_primary),
                    "succeeded_count": sum(
                        row["outcome"]["execution_status"] == "succeeded"
                        for row in matching_acquisitions
                    ),
                    "failed_count": sum(
                        row["outcome"]["execution_status"] == "failed"
                        for row in matching_acquisitions
                    ),
                }
            )
        target_rows.append(
            {
                "qualified_source_route": source,
                "source_id": source_id,
                "scientific_role": target["scientific_role"],
                "found_in_primary_aggregate": found_in_aggregate,
                "enrichment_routes": route_rows,
                "status": (
                    "missing"
                    if not found_in_aggregate
                    else "present_no_enrichment"
                    if not route_rows
                    else "succeeded"
                    if all(row["succeeded_count"] >= 1 for row in route_rows)
                    else "failed_or_unavailable"
                ),
            }
        )
    expected_route_count = sum(
        len(target["enrichment_routes"]) for target in spec["stage_2_targets"]
    )
    executed_route_count = sum(
        row["executed_count"]
        for target in target_rows
        for row in target["enrichment_routes"]
    )
    succeeded_route_count = sum(
        row["succeeded_count"]
        for target in target_rows
        for row in target["enrichment_routes"]
    )
    return {
        "preregistered_target_count": len(target_rows),
        "found_target_count": sum(
            row["found_in_primary_aggregate"] for row in target_rows
        ),
        "missing_target_count": sum(row["status"] == "missing" for row in target_rows),
        "expected_enrichment_route_count": expected_route_count,
        "executed_enrichment_route_count": executed_route_count,
        "succeeded_enrichment_route_count": succeeded_route_count,
        "failed_or_unavailable_enrichment_route_count": expected_route_count
        - succeeded_route_count,
        "targets": target_rows,
        "qualified_source_route_count": len(raw["qualified_source_routes"]),
        "target_followup_run_count": len(target_runs),
        "additional_source_record_acquisition_count": len(
            additional_discovery_acquisitions
        ),
        "passed": (
            all(
                row["status"] in {"present_no_enrichment", "succeeded"}
                for row in target_rows
            )
            and executed_route_count == expected_route_count
            and succeeded_route_count == expected_route_count
            and not additional_discovery_acquisitions
            and all(
                route["bound_to_primary_discovery_count"] == route["executed_count"]
                for target in target_rows
                for route in target["enrichment_routes"]
            )
        ),
    }


def _shared_discovery_capture_audit(raw: dict[str, Any]) -> dict[str, Any]:
    primary_runs = [
        run for run in raw["runs"] if run["run_role"] == "primary_aggregate"
    ]
    if len(primary_runs) != 1:
        return {
            "aggregate_source_records_call_count": raw.get(
                "aggregate_source_records_call_count"
            ),
            "primary_aggregate_run_count": len(primary_runs),
            "additional_source_record_acquisition_count": None,
            "passed": False,
        }
    primary = primary_runs[0]
    requirements = primary["requirements"]
    requirement = requirements[0] if len(requirements) == 1 else {}
    constraints = requirement.get("operational_constraints") or {}
    retrieval = constraints.get("retrieval") or {}
    discovery_acquisitions = [
        acquisition
        for run in raw["runs"]
        for acquisition in run["acquisitions"]
        if acquisition["route"]["operation"] == "search_materials"
    ]
    primary_acquisition_ids = {
        acquisition["acquisition_id"] for acquisition in primary["acquisitions"]
    }
    additional_discovery = [
        acquisition
        for acquisition in discovery_acquisitions
        if acquisition["acquisition_id"] not in primary_acquisition_ids
    ]
    bundle = primary["canonical_bundle"]
    summary = raw.get("shared_discovery_ledger") or {}
    ready_route_count = sum(
        _route_is_ready(route) and route["operation"] == "search_materials"
        for route in primary["routes"]
    )
    passed = (
        raw.get("aggregate_source_records_call_count") == 1
        and len(requirements) == 1
        and requirement.get("evidence_kind") == "source_record"
        and constraints.get("sources") == []
        and retrieval.get("record_scope") == "exhaust_upstream"
        and raw.get("retrieval_strategy", {}).get("shared_discovery_policy")
        == SHARED_DISCOVERY_POLICY
        and len(primary["acquisitions"]) == ready_route_count
        and not additional_discovery
        and summary.get("authoritative_bundle_id") == bundle["bundle_id"]
        and summary.get("source_record_count")
        == len(_bundle_items(bundle, "source_record"))
        and summary.get("rq1_rq2_same_bundle") is True
    )
    return {
        "aggregate_source_records_call_count": raw.get(
            "aggregate_source_records_call_count"
        ),
        "primary_aggregate_run_count": 1,
        "ready_route_count": ready_route_count,
        "primary_discovery_acquisition_count": len(primary["acquisitions"]),
        "additional_source_record_acquisition_count": len(additional_discovery),
        "authoritative_bundle_id": bundle["bundle_id"],
        "rq1_rq2_same_bundle": summary.get("rq1_rq2_same_bundle"),
        "passed": passed,
    }


def _capture_protocol_status(
    raw: dict[str, Any], spec: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    if raw.get("protocol_version") == PROTOCOL_VERSION:
        aggregate_runs = [
            row for row in raw["runs"] if row["run_role"] == "primary_aggregate"
        ]
        aggregate_summary = (
            _aggregate_summary(aggregate_runs[0]["canonical_bundle"])
            if len(aggregate_runs) == 1
            else None
        )
        aggregate_closed = bool(
            aggregate_summary
            and aggregate_summary["qualified_route_count"]
            == len(raw["qualified_source_routes"])
            and aggregate_summary["attempted_route_count"]
            == aggregate_summary["ready_route_count"]
            and aggregate_summary["all_ready_routes_have_execution"]
            and aggregate_summary["all_qualified_routes_attempted"]
            and aggregate_summary["real_cross_source_records"]
        )
        shared_discovery_audit = _shared_discovery_capture_audit(raw)
        conformance = {
            "single_primary_all_route_aggregate": aggregate_closed,
            "primary_aggregate_summary": aggregate_summary,
            "run_roles_valid": all(
                row["run_role"]
                in {
                    "primary_aggregate",
                    "target_followup",
                    "thermochemical",
                }
                for row in raw["runs"]
            ),
            "shared_discovery_ledger": shared_discovery_audit,
            "stage_2_preregistered_exact_targets": True,
            "capture_eligible_under_frozen_protocol": aggregate_closed
            and shared_discovery_audit["passed"],
            "reason": None,
        }
        if spec is not None:
            audit = _stage2_target_audit(raw, spec)
            conformance["stage_2_target_audit"] = audit
            conformance["capture_eligible_under_frozen_protocol"] = (
                aggregate_closed
                and conformance["run_roles_valid"]
                and shared_discovery_audit["passed"]
                and audit["passed"]
            )
        return raw["retrieval_strategy"], conformance
    raise ValueError("capture protocol does not match the active single-track protocol")


def _subject(
    formula: str | None = None,
    elements: tuple[str, ...] = (),
    material_id: str | None = None,
) -> Any:
    from matrouter.evidence_contracts import SubjectScope

    return SubjectScope(formula=formula, elements=elements, material_id=material_id)


def _constraints(
    *,
    sources: tuple[str, ...] = (),
    all_qualified: bool = False,
    filters: tuple[Any, ...] = (),
) -> Any:
    from matrouter.evidence_contracts import OperationalConstraints
    from matrouter.retrieval import RetrievalStrategy

    return OperationalConstraints(
        sources=() if all_qualified else sources,
        retrieval=RetrievalStrategy(record_scope="exhaust_upstream"),
        filters=filters,
    )


def _create_requirement(
    tools: Any,
    run_id: str,
    *,
    subject: Any,
    kind: str,
    constraints: Any,
) -> Any:
    from matrouter.tools.evidence import CreateEvidenceRequirementRequest

    return tools.create_evidence_requirement(
        CreateEvidenceRequirementRequest(
            evidence_run_id=run_id,
            subject_scope=subject,
            evidence_kind=kind,
            operational_constraints=constraints,
        )
    )


def _execute(
    tools: Any,
    run_id: str,
    requirement: Any,
    route: Any,
    attempt_id: str,
    *,
    input_acquisition: Any | None = None,
    input_record_ref: Any | None = None,
) -> Any:
    from matrouter.tools.evidence import ExecuteEvidenceRouteToolRequest

    if route.operation == "search_materials":
        raise ValueError(
            "Source-record discovery is owned exclusively by the case's single "
            "aggregate_source_records call"
        )
    return tools.execute_evidence_route(
        ExecuteEvidenceRouteToolRequest(
            evidence_run_id=run_id,
            requirement=requirement,
            route=route,
            attempt_id=attempt_id,
            input_acquisition_id=(
                input_acquisition.acquisition_id
                if input_acquisition is not None
                else None
            ),
            input_record_ref=input_record_ref,
        )
    )


def _route(tools: Any, run_id: str, requirement: Any) -> list[Any]:
    from matrouter.tools.evidence import RouteRequirementsRequest

    return list(
        tools.route_evidence_requirements(
            RouteRequirementsRequest(
                evidence_run_id=run_id, requirements=(requirement,)
            )
        ).route_candidates
    )


def _safe_label(value: str) -> str:
    return (
        "".join(character if character.isalnum() else "-" for character in value)
        .strip("-")
        .lower()
    )


def _all_exact_refs(acquisitions: list[Any]) -> list[tuple[Any, Any]]:
    refs: list[tuple[Any, Any]] = []
    for acquisition in acquisitions:
        for record_ref in acquisition.record_refs:
            refs.append((acquisition, record_ref))
    return sorted(
        refs,
        key=lambda row: (
            row[1].source,
            row[1].source_id,
            row[1].record_content_id,
            row[0].acquisition_id,
        ),
    )


def _registered_acquisitions(
    registry: Any, run_id: str, *, requirement_ids: set[str] | None = None
) -> list[Any]:
    """Snapshot exact acquisitions already committed by MatRouter in one run ledger."""
    with registry.borrow(run_id) as state:
        acquisitions = list(state.acquisitions.values())
    if requirement_ids is not None:
        acquisitions = [
            row
            for row in acquisitions
            if row.requirement.requirement_id in requirement_ids
        ]
    return sorted(acquisitions, key=lambda row: row.acquisition_id)


def _add_bound_detail(
    *,
    tools: Any,
    run_id: str,
    case_name: str,
    formula: str,
    source: str,
    kind: str,
    operation: str,
    discovery_acquisition: Any,
    record_ref: Any,
    requirements: list[Any],
    routes: list[Any],
    acquisitions: list[Any],
) -> None:
    record_label = _safe_label(
        f"{record_ref.source_id}-{record_ref.record_content_id}"
    )[-80:]
    requirement = _create_requirement(
        tools,
        run_id,
        subject=_subject(formula=formula),
        kind=kind,
        constraints=_constraints(sources=(source,)),
    )
    if all(
        existing.requirement_id != requirement.requirement_id
        for existing in requirements
    ):
        requirements.append(requirement)
    candidates = _route(tools, run_id, requirement)
    existing_route_ids = {route.route_id for route in routes}
    routes.extend(
        route for route in candidates if route.route_id not in existing_route_ids
    )
    selected = [
        route for route in candidates if route.operation == operation and route.is_ready
    ]
    for index, selected_route in enumerate(
        sorted(selected, key=lambda route: route.route_id)
    ):
        acquisitions.append(
            _execute(
                tools,
                run_id,
                requirement,
                selected_route,
                f"paper-protocol-v1-{case_name}-{_safe_label(source)}-{record_label}-{kind}-{index:02d}",
                input_acquisition=discovery_acquisition,
                input_record_ref=record_ref,
            )
        )


def _bundle_items(bundle: dict[str, Any], item_kind: str) -> list[dict[str, Any]]:
    return [item for item in bundle["evidence_items"] if item["item_kind"] == item_kind]


def _record_from_item(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("item_kind") != "source_record":
        raise ValueError("expected one source_record evidence item")
    record = json.loads(item["content"])
    if not isinstance(record, dict):
        raise TypeError("SourceRecordItem content must be a JSON object")
    return record


def _artifact_content(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("item_kind") != "scientific_artifact":
        raise ValueError("expected one scientific_artifact evidence item")
    content = json.loads(item["content"])
    if not isinstance(content, dict):
        raise TypeError("ScientificArtifactItem content must be a JSON object")
    return content


def _thermochemical_entry_count(item: dict[str, Any]) -> int:
    content = _artifact_content(item)
    entries = content.get("entries")
    if not isinstance(entries, list):
        raise TypeError("thermochemical entry-set content must contain entries")
    return len(entries)


def _route_is_ready(route: dict[str, Any]) -> bool:
    return route.get("missing_setting") is None


def _route_state(route: dict[str, Any]) -> str:
    return "ready" if _route_is_ready(route) else "requires_configuration"


def _route_aggregate_sources(route: dict[str, Any]) -> list[str]:
    return list(route.get("aggregate_sources") or [])


def _route_accepts_source(route: dict[str, Any], source: str) -> bool:
    allowed = _route_aggregate_sources(route) or [route["qualified_source"]]
    return source in allowed


def _derived_record_result(outcome: dict[str, Any], operation: str) -> str | None:
    from matrouter.evidence_contracts import SourceOutcomePayload, record_result

    return record_result(
        SourceOutcomePayload.model_validate(wire(outcome)), operation=operation
    )


def _execution_elapsed_seconds(execution: dict[str, Any]) -> float:
    started = datetime.fromisoformat(execution["started_at"])
    completed = datetime.fromisoformat(execution["completed_at"])
    return round((completed - started).total_seconds(), 6)


def _bundle_execution_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    routes = {route["route_id"]: route for route in bundle["routes"]}
    requirements = {
        requirement["requirement_id"]: requirement
        for requirement in bundle["requirements"]
    }
    evidence_items = {item["item_id"]: item for item in bundle["evidence_items"]}
    rows: list[dict[str, Any]] = []
    for execution in bundle["executions"]:
        route = routes[execution["route_id"]]
        requirement = requirements[route["requirement_id"]]
        outcome = execution["outcome"]
        completeness = outcome.get("record_completeness")
        output_items = [
            evidence_items[item_id] for item_id in execution["output_item_ids"]
        ]
        source_record_items = [
            item for item in output_items if item["item_kind"] == "source_record"
        ]
        rows.append(
            {
                "attempt_id": execution["attempt_id"],
                "route_id": route["route_id"],
                "requirement_id": route["requirement_id"],
                "qualified_source": route["qualified_source"],
                "aggregate_sources": _route_aggregate_sources(route),
                "operation": route["operation"],
                "execution_status": outcome["execution_status"],
                "record_completeness": completeness,
                "record_result": _derived_record_result(outcome, route["operation"]),
                "reason_code": outcome["reason_code"],
                "failure_type": outcome.get("failure_type"),
                "message": outcome.get("message"),
                "warnings": execution.get("warnings") or [],
                "output_item_ids": execution["output_item_ids"],
                "output_items": output_items,
                "source_record_items": source_record_items,
                "source_record_count": len(source_record_items),
                "returned_count": (
                    completeness["returned_count"] if completeness is not None else 0
                ),
                "elapsed_seconds": _execution_elapsed_seconds(execution),
                "operational_constraints": requirement["operational_constraints"],
            }
        )
    return rows


def _case_bundles(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [capsule["evidence_bundle"] for capsule in result["evidence_bundles"]]


def _primary_aggregate_bundle(result: dict[str, Any]) -> dict[str, Any]:
    bundles = [
        capsule["evidence_bundle"]
        for capsule in result["evidence_bundles"]
        if capsule["bundle_role"] == "primary_aggregate"
    ]
    if len(bundles) != 1:
        raise ValueError(
            f"{result['case_name']}: expected one primary aggregate Bundle"
        )
    return bundles[0]


def _target_bundles(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        capsule["evidence_bundle"]
        for capsule in result["evidence_bundles"]
        if capsule["bundle_role"] in {"target_followup", "thermochemical"}
    ]


def _case_items(result: dict[str, Any], item_kind: str) -> list[dict[str, Any]]:
    return [
        item
        for bundle in _case_bundles(result)
        for item in _bundle_items(bundle, item_kind)
    ]


def _aggregate_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    from matrouter.evidence_contracts import SourceRecordItem

    executions = _bundle_execution_rows(bundle)
    source_records = _bundle_items(bundle, "source_record")
    record_identities = [
        SourceRecordItem.model_validate(wire(item)).identity for item in source_records
    ]
    record_sources = sorted({identity.source for identity in record_identities})
    provider_identity_complete = bool(record_identities) and all(
        identity.provider for identity in record_identities
    )
    record_providers = sorted({identity.provider for identity in record_identities})
    real_cross_source_records = (
        len(record_sources) >= 2
        and provider_identity_complete
        and len(record_providers) >= 2
    )
    execution_rows = [
        {
            "qualified_source": execution["qualified_source"],
            "aggregate_sources": execution["aggregate_sources"],
            "operation": execution["operation"],
            "execution_status": execution["execution_status"],
            "record_result": execution["record_result"],
            "reason_code": execution["reason_code"],
            "record_count": execution["source_record_count"],
            "returned_count": execution["returned_count"],
            "record_completeness": execution["record_completeness"],
            "warning_count": len(execution["warnings"]),
            "warnings": execution["warnings"],
            "elapsed_seconds": execution["elapsed_seconds"],
        }
        for execution in sorted(
            executions,
            key=lambda row: (
                row["qualified_source"],
                row["operation"],
                row["attempt_id"],
            ),
        )
    ]
    completeness_counts = Counter(
        execution["record_completeness"]["state"]
        for execution in executions
        if execution["record_completeness"] is not None
    )
    record_result_counts = Counter(
        execution["record_result"]
        for execution in executions
        if execution["record_result"] is not None
    )
    capacity_limitations = [
        row
        for row in execution_rows
        if (row.get("record_completeness") or {}).get("state") == "truncated"
        or row["reason_code"] == "evidence_run_capacity_exceeded"
    ]
    qualified_sources = sorted(row["qualified_source"] for row in bundle["routes"])
    ready_sources = sorted(
        row["qualified_source"] for row in bundle["routes"] if _route_is_ready(row)
    )
    execution_sources = sorted(row["qualified_source"] for row in executions)
    all_ready_routes_have_execution = (
        len(execution_sources) == len(set(execution_sources))
        and execution_sources == ready_sources
    )
    return {
        "bundle_id": bundle["bundle_id"],
        "semantics": "The one primary agent-facing EvidenceBundle produced by aggregate_source_records through bounded parallel cross-source execution with at most eight workers and stable-order aggregation; scientific evidence_items remain separate from the per-route executions that embed outcomes and warnings.",
        "bundle_canonical_bytes": len(canonical_bytes(bundle)),
        "evidence_item_count": len(bundle["evidence_items"]),
        "execution_count": len(bundle["executions"]),
        "execution_routes": [
            {
                "qualified_source": row["qualified_source"],
                "aggregate_sources": _route_aggregate_sources(row),
                "state": _route_state(row),
            }
            for row in bundle["routes"]
        ],
        "qualified_route_count": len(bundle["routes"]),
        "ready_route_count": len(ready_sources),
        "attempted_route_count": len(executions),
        "all_ready_routes_have_execution": all_ready_routes_have_execution,
        "all_qualified_routes_ready": ready_sources == qualified_sources,
        "all_qualified_routes_attempted": execution_sources == qualified_sources,
        "source_record_count": len(source_records),
        "source_record_sources": record_sources,
        "source_record_source_count": len(record_sources),
        "source_record_providers": record_providers,
        "source_record_provider_count": len(record_providers),
        "source_record_provider_identity_complete": provider_identity_complete,
        "real_cross_source_records": real_cross_source_records,
        "execution_status_counts": dict(
            sorted(Counter(row["execution_status"] for row in executions).items())
        ),
        "record_result_counts": dict(sorted(record_result_counts.items())),
        "record_completeness_counts": dict(sorted(completeness_counts.items())),
        "capacity_limitations": capacity_limitations,
        "total_warning_count": sum(len(row["warnings"]) for row in executions),
        "executions": execution_rows,
        "materials_galaxy_parent_outcome_semantics": "The provider-level MaterialsGalaxy execution describes one combined summary query. aggregate_sources declare the accepted child authorities; child record provenance does not establish a separate child execution outcome or closure result.",
    }


def _property_occurrences(
    bundle: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """Yield normalized property occurrences for the paper observation export."""
    for item in bundle["evidence_items"]:
        if item["item_kind"] != "source_record":
            continue
        record = _record_from_item(item)
        container_source = record["source"]
        container_source_id = record["source_id"]
        property_observations = record.get("property_observations") or {}
        if not isinstance(property_observations, dict):
            raise TypeError("SourceRecordItem property_observations must be an object")
        for property_name, property_value in property_observations.items():
            if not isinstance(property_value, dict):
                raise TypeError("normalized property observation must be an object")
            occurrences = property_value.get("observations")
            if occurrences is None:
                occurrences = [property_value]
            if not isinstance(occurrences, list):
                raise TypeError("normalized property observations must be a list")
            for observation in occurrences:
                if not isinstance(observation, dict):
                    raise TypeError("normalized property occurrence must be an object")
                provenance = observation.get("provenance") or {}
                if not isinstance(provenance, dict):
                    raise TypeError("property observation provenance must be an object")
                yield {
                    "item": item,
                    "record": record,
                    "observation": observation,
                    "observation_fields": {
                        "source": provenance.get("evidence_source") or container_source,
                        "source_id": provenance.get("evidence_source_id")
                        or container_source_id,
                        "formula": record.get("formula"),
                        "property": property_name,
                        "value": observation.get("value"),
                        "unit": observation.get("unit"),
                    },
                }


def _record_data_categories(record: dict[str, Any]) -> list[str]:
    categories = {"material_identity"}
    metadata = record.get("source_metadata") or {}
    if any(
        record.get(key) is not None
        for key in ("nsites", "space_group_number", "space_group_symbol")
    ) or any(
        metadata.get(key) is not None
        for key in (
            "dimensionality",
            "nperiodic_dimensions",
            "layer_group_symbol",
            "prototype",
        )
    ):
        categories.add("structure_or_phase")
    for property_name in record.get("property_observations") or {}:
        if property_name == "band_gap_eV":
            categories.add("electronic_property")
        if property_name.startswith("topology_class_"):
            categories.add("source_native_topology")
        if property_name in {
            "energy_above_hull_eV",
            "formation_energy_per_atom_eV",
            "formation_enthalpy_per_atom_eV",
            "heat_of_formation_per_atom_eV",
            "is_stable",
        }:
            categories.add("thermodynamic_property")
    return sorted(categories)


def _compact_observation_context(observation: dict[str, Any]) -> dict[str, Any]:
    relevant_keys = {
        "code",
        "dimensionality",
        "functional",
        "gap_character",
        "gap_observable_level",
        "hull_construction",
        "method_family",
        "modality",
        "relativity_method",
        "soc",
        "spin",
        "stability_definition",
        "thermo_type",
        "workflow",
    }
    return {
        key: value
        for key, value in (observation.get("context") or {}).items()
        if key in relevant_keys
        and value is not None
        and len(canonical_json(value)) <= 500
    }


def _record_context_summary(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("source_metadata") or {}
    structure_context = {
        key: value
        for key, value in {
            "space_group_symbol": record.get("space_group_symbol"),
            "space_group_number": record.get("space_group_number"),
            "dimensionality": metadata.get("dimensionality"),
            "nperiodic_dimensions": metadata.get("nperiodic_dimensions"),
            "layer_group_symbol": metadata.get("layer_group_symbol"),
            "prototype": metadata.get("prototype"),
        }.items()
        if value is not None
    }
    method_context = {
        key: metadata[key]
        for key in (
            "dft_type",
            "functional_status",
            "method_name",
            "dft_method_context",
            "magnetic",
        )
        if metadata.get(key) is not None and len(canonical_json(metadata[key])) <= 500
    }
    observation_contexts: list[dict[str, Any]] = []
    for property_name, value in (record.get("property_observations") or {}).items():
        occurrences = value.get("observations") if isinstance(value, dict) else None
        if occurrences is None:
            occurrences = [value]
        for observation in occurrences:
            if not isinstance(observation, dict):
                continue
            context = _compact_observation_context(observation)
            if context:
                observation_contexts.append(
                    {"property": property_name, "context": context}
                )
    return {
        "structure_or_phase": structure_context,
        "method_or_observable": method_context,
        "property_contexts": observation_contexts,
    }


def _representative_record(
    item: dict[str, Any], record: dict[str, Any]
) -> dict[str, Any]:
    observations = []
    for occurrence in _property_occurrences(
        {
            "evidence_items": [item],
        }
    ):
        fields = occurrence["observation_fields"]
        observation = occurrence["observation"]
        observations.append(
            {
                **fields,
                "semantic": observation.get("semantic"),
                "context": _compact_observation_context(observation),
            }
        )
    return {
        "selection_rule": "first record for this exact source in stable primary-Bundle order; not selected by value or scientific favorability",
        "source_record_item_id": item["item_id"],
        "source_id": record["source_id"],
        "formula": record.get("formula"),
        "context": _record_context_summary(record),
        "observations": observations,
    }


def _source_contribution_map(
    bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from matrouter.evidence_contracts import SourceRecordItem

    contributions: dict[str, dict[str, Any]] = {}
    for bundle in bundles:
        executions = _bundle_execution_rows(bundle)
        executions_by_output_item: dict[str, list[dict[str, Any]]] = {}
        for execution in executions:
            for item_id in execution["output_item_ids"]:
                executions_by_output_item.setdefault(item_id, []).append(execution)
        for item in _bundle_items(bundle, "source_record"):
            identity = SourceRecordItem.model_validate(wire(item)).identity
            record = _record_from_item(item)
            matching_executions = executions_by_output_item.get(item["item_id"], [])
            if len(matching_executions) != 1:
                raise ValueError(
                    f"{identity.source}:{identity.source_id}: exact execution binding is ambiguous"
                )
            execution = matching_executions[0]
            if not _route_accepts_source(
                {
                    "qualified_source": execution["qualified_source"],
                    "aggregate_sources": execution["aggregate_sources"],
                },
                identity.source,
            ):
                raise ValueError(
                    f"{identity.source}: contributing source is outside its execution route"
                )
            contribution = contributions.setdefault(
                identity.source,
                {
                    "source": identity.source,
                    "provider": identity.provider,
                    "execution_route": execution["qualified_source"],
                    "execution_status": execution["execution_status"],
                    "record_result": execution["record_result"],
                    "record_completeness": execution["record_completeness"],
                    "record_count_in_shared_discovery": 0,
                    "data_categories": set(),
                    "property_names": set(),
                    "representative_record": _representative_record(item, record),
                },
            )
            contribution["record_count_in_shared_discovery"] += 1
            contribution["data_categories"].update(_record_data_categories(record))
            contribution["property_names"].update(
                (record.get("property_observations") or {}).keys()
            )
    return [
        {
            **row,
            "data_categories": sorted(row["data_categories"]),
            "property_names": sorted(row["property_names"]),
        }
        for row in contributions.values()
    ]


def _method_trace(method: dict[str, Any]) -> dict[str, Any]:
    name = method["method_name"]
    result = method["result"]
    summary: dict[str, Any]
    if name == "match_structures":
        summary = {
            "matched": result["matched"],
            "distance_status": result["distance_status"],
            "parameters": result["parameters"],
        }
    elif name in {"render_band_structure", "render_density_of_states"}:
        summary = {
            "input": result["input"],
            "plot_artifact": result["plot_artifact"],
        }
    elif name == "compute_phase_diagrams":
        dataset = result["datasets"][0]
        input_manifest = dataset["input_manifest"]
        entry_set = input_manifest["entry_set"]
        thermochemical_context = json.loads(entry_set["content"])[
            "thermochemical_context"
        ]
        summary = {
            "entry_count": len(dataset["entries"]),
            "input_manifest_id": input_manifest["manifest_id"],
            "entry_set_item_id": entry_set["item_id"],
            "dataset": thermochemical_context["dataset"],
            "thermo_type": thermochemical_context["thermo_types"][0],
            "energy_frame": thermochemical_context["energy_frame"],
            "method_parameters": result["method_parameters"],
            "plot_artifact": dataset["plot_artifact"],
        }
    else:
        raise ValueError(f"unsupported explicit method in case trace: {name}")
    return {
        "method_name": name,
        "succeeded": _method_result_succeeded(method),
        "input_bundle_ids": method.get("input_bundle_ids")
        or [method["input_bundle_id"]],
        "exact_input_item_ids": method["exact_input_item_ids"],
        "result": summary,
    }


def _material_landscape_trace(
    result: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    primary = _primary_aggregate_bundle(result)
    contributions = _source_contribution_map([primary])
    contributions_by_source = {row["source"]: row for row in contributions}
    union_claims: list[dict[str, Any]] = []
    unsupported_claim_gaps: list[dict[str, Any]] = []
    for claim in spec["material_landscape"]["cross_source_union_adds"]:
        missing_support: list[dict[str, Any]] = []
        non_exhaustive_support: list[dict[str, Any]] = []
        for support in claim["supporting_contributions"]:
            contribution = contributions_by_source.get(support["source"])
            required_categories = set(support["data_categories"])
            actual_categories = set(
                contribution["data_categories"] if contribution is not None else []
            )
            if contribution is None or not required_categories <= actual_categories:
                missing_support.append(
                    {
                        "source": support["source"],
                        "required_data_categories": sorted(required_categories),
                        "actual_data_categories": sorted(actual_categories),
                        "reason": (
                            "source_not_returned"
                            if contribution is None
                            else "required_data_categories_not_returned"
                        ),
                    }
                )
            elif contribution["record_completeness"]["state"] != "complete":
                non_exhaustive_support.append(
                    {
                        "source": support["source"],
                        "execution_route": contribution["execution_route"],
                        "execution_status": contribution["execution_status"],
                        "record_result": contribution["record_result"],
                        "record_completeness": contribution["record_completeness"][
                            "state"
                        ],
                        "reason": "support_is_observed_but_source_not_exhausted",
                    }
                )
        support_status = "supported" if not missing_support else "unsupported"
        complete_inventory_support_status = (
            "eligible"
            if support_status == "supported" and not non_exhaustive_support
            else "ineligible"
        )
        union_claims.append(
            {
                **claim,
                "support_status": support_status,
                "missing_supporting_contributions": missing_support,
                "complete_inventory_support_status": complete_inventory_support_status,
                "non_exhaustive_supporting_contributions": non_exhaustive_support,
            }
        )
        if missing_support:
            unsupported_claim_gaps.append(
                {
                    "statement": claim["statement"],
                    "sources": [row["source"] for row in missing_support],
                    "missing_supporting_contributions": missing_support,
                }
            )
    aggregate = result["aggregate"]
    scientific_rows = _paper_scientific_rows(result)
    return {
        "case_name": result["case_name"],
        "scientific_task": spec["scientific_question"],
        "primary_aggregate_bundle_id": primary["bundle_id"],
        "rq1_rq2_authoritative_bundle_id": primary["bundle_id"],
        "declared_source_scope": {
            "catalog_and_configuration": "MatRouter v0.10.2 capability catalog under the captured runtime configuration",
            **spec["stage_1"],
            "scope_limit": "All capability-matched execution routes were attempted within the declared budgets; this is not every real-world database or every upstream record.",
        },
        "route_outcome_summary": {
            "qualified": aggregate["qualified_route_count"],
            "ready": aggregate["ready_route_count"],
            "attempted": aggregate["attempted_route_count"],
            "execution_status_counts": aggregate["execution_status_counts"],
            "record_result_counts": aggregate["record_result_counts"],
            "record_completeness_counts": aggregate["record_completeness_counts"],
            "executions": [
                {
                    "qualified_source": execution["qualified_source"],
                    "execution_status": execution["execution_status"],
                    "record_result": execution["record_result"],
                    "record_count": execution["record_count"],
                    "reason_code": execution["reason_code"],
                    "completeness": (execution.get("record_completeness") or {}).get(
                        "state"
                    ),
                    "truncation_reason": (
                        execution.get("record_completeness") or {}
                    ).get("truncation_reason"),
                    "warnings": execution["warnings"],
                }
                for execution in aggregate["executions"]
            ],
        },
        "shared_discovery_ledger": result["shared_discovery_ledger"],
        "rq2_interpretation_boundary": {
            "observed_landscape_supported": not unsupported_claim_gaps,
            "complete_inventory_eligible": result["shared_discovery_ledger"][
                "complete_inventory_eligible"
            ],
            "semantics": "RQ2 reads the exact executions and source-record items already used by RQ1. Observed records may support a source-qualified landscape even when an execution failed or completeness is unknown or truncated; complete-inventory wording requires every ready route in that same Bundle to be complete or verified empty.",
        },
        "contributing_exact_sources": contributions,
        "provider_groups": aggregate["source_record_providers"],
        "data_categories_actually_present": sorted(
            {
                category
                for contribution in contributions
                for category in contribution["data_categories"]
            }
        ),
        "what_cross_source_union_adds": union_claims,
        "all_declared_claims_supported": not unsupported_claim_gaps,
        "unsupported_declared_claim_gaps": unsupported_claim_gaps,
        "exact_followups": {
            "target_audit": result["protocol_conformance"]["stage_2_target_audit"],
            "artifacts": scientific_rows["artifacts"],
            "thermochemical_entry_sets": [
                {
                    "item_id": item["item_id"],
                    "source": item["identity"]["source"],
                    "source_id": item["identity"]["source_id"],
                    "entry_count": _thermochemical_entry_count(item),
                }
                for item in _case_items(result, "scientific_artifact")
                if item["artifact_type"] == "thermochemical_entry_set"
            ],
            "methods": [_method_trace(method) for method in result["explicit_methods"]],
        },
        "researcher_use": spec["material_landscape"]["researcher_use"],
        "actionable_next_step": spec["next_action"],
        "external_handoff": spec["material_landscape"]["external_handoff"],
        "unresolved_gaps": spec["missing_evidence"],
        "prohibited_claims": spec["prohibited_statement"],
    }


def _paper_scientific_rows(
    result: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    case_name = result["case_name"]
    primary = _primary_aggregate_bundle(result)
    observations: list[dict[str, Any]] = []
    structures: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for occurrence in _property_occurrences(primary):
        item = occurrence["item"]
        observation = occurrence["observation"]
        observation_fields = occurrence["observation_fields"]
        observations.append(
            {
                "case_name": case_name,
                "source": observation_fields["source"],
                "source_id": observation_fields["source_id"],
                "formula": observation_fields["formula"],
                "property": observation_fields["property"],
                "semantic": observation.get("semantic"),
                "value_json": canonical_json(observation_fields["value"]),
                "unit": observation_fields["unit"],
                "context_json": canonical_json(observation.get("context") or {}),
                "provenance_json": canonical_json(observation.get("provenance") or {}),
                "limitations_json": canonical_json(
                    observation.get("limitations") or []
                ),
                "record_item_id": item["item_id"],
            }
        )
    for bundle in [primary, *_target_bundles(result)]:
        for item in bundle["evidence_items"]:
            if item["item_kind"] == "structure":
                identity = item["identity"]
                content = item["content"]
                parsed_content = (
                    json.loads(content)
                    if item["media_type"] == "application/json"
                    else content
                )
                structures.append(
                    {
                        "case_name": case_name,
                        "source": identity["source"],
                        "source_id": identity["source_id"],
                        "structure_item_id": item["item_id"],
                        "media_type": item["media_type"],
                        "content_sha256": sha256_bytes(content.encode()),
                        "content_bytes": len(content.encode()),
                        "pbc_json": canonical_json(parsed_content.get("pbc"))
                        if isinstance(parsed_content, dict)
                        else "null",
                    }
                )
            elif item["item_kind"] == "scientific_artifact":
                identity = item["identity"]
                content = _artifact_content(item)
                artifacts.append(
                    {
                        "case_name": case_name,
                        "source": identity["source"],
                        "source_id": identity["source_id"],
                        "artifact_item_id": item["item_id"],
                        "artifact_type": item["artifact_type"],
                        "content_sha256": sha256_bytes(item["content"].encode()),
                        "content_bytes": len(item["content"].encode()),
                        "content_json": canonical_json(content),
                    }
                )
    return {
        "observations": observations,
        "structures": structures,
        "artifacts": artifacts,
    }


def _aggregate_coverage_rows(
    case_name: str, bundle: dict[str, Any]
) -> list[dict[str, Any]]:
    executions = {
        row["qualified_source"]: row
        for row in _bundle_execution_rows(bundle)
        if row["operation"] == "search_materials"
    }
    rows: list[dict[str, Any]] = []
    for route in sorted(bundle["routes"], key=lambda row: row["qualified_source"]):
        execution = executions.get(route["qualified_source"])
        completeness = (execution or {}).get("record_completeness") or {}
        record_result = (execution or {}).get("record_result")
        rows.append(
            {
                "case_name": case_name,
                "source": route["qualified_source"],
                "aggregate_sources_json": canonical_json(
                    _route_aggregate_sources(route)
                ),
                "qualified": True,
                "route_state": _route_state(route),
                "executed": execution is not None,
                "execution_status": (
                    execution["execution_status"]
                    if execution is not None
                    else "not_executed"
                ),
                "record_result": record_result or "not_executed",
                "succeeded": execution is not None
                and execution["execution_status"] == "succeeded",
                "verified_empty": record_result == "empty",
                "truncated": record_result == "truncated",
                "upstream_total_unknown": record_result == "upstream_total_unknown",
                "failed": record_result == "failed",
                "record_count": (
                    execution["source_record_count"] if execution is not None else 0
                ),
                "returned_count": completeness.get("returned_count"),
                "completeness": completeness.get("state", "not_applicable"),
                "upstream_total": completeness.get("upstream_total"),
                "pages_fetched": completeness.get("pages_fetched", 0),
                "truncation_reason": completeness.get("truncation_reason"),
                "reason_code": (
                    execution["reason_code"]
                    if execution is not None
                    else "route_not_ready"
                ),
                "warning_count": (
                    len(execution["warnings"]) if execution is not None else 0
                ),
                "warnings_json": canonical_json(
                    execution["warnings"] if execution is not None else []
                ),
                "elapsed_seconds": (
                    execution["elapsed_seconds"] if execution is not None else None
                ),
            }
        )
    return rows


def _source_outcome_audit_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = _primary_aggregate_bundle(result)
    executions = {
        row["qualified_source"]: row
        for row in _bundle_execution_rows(bundle)
        if row["operation"] == "search_materials"
    }

    rows: list[dict[str, Any]] = []
    for route in sorted(bundle["routes"], key=lambda row: row["qualified_source"]):
        qualified_source = route["qualified_source"]
        execution = executions[qualified_source]
        actual_sources = [
            _record_from_item(item)["source"]
            for item in execution["source_record_items"]
        ]
        actual_count = len(actual_sources)
        completeness = execution["record_completeness"]
        if completeness is None:
            returned_count = 0
        else:
            returned_count = completeness["returned_count"]
        constraints = execution["operational_constraints"]
        retrieval = constraints["retrieval"]
        rows.append(
            {
                "case_name": result["case_name"],
                "qualified_source_route": qualified_source,
                "aggregate_sources_json": canonical_json(
                    _route_aggregate_sources(route)
                ),
                "route_state": _route_state(route),
                "execution_status": execution["execution_status"],
                "record_result": execution["record_result"],
                "reason_code": execution["reason_code"],
                "record_count": execution["source_record_count"],
                "returned_count": returned_count,
                "actual_bundle_record_count": actual_count,
                "actual_bundle_record_sources_json": canonical_json(
                    sorted(Counter(actual_sources).items())
                ),
                "record_count_matches_actual": execution["source_record_count"]
                == actual_count,
                "returned_count_matches_actual": returned_count == actual_count,
                "record_completeness_state": (
                    completeness["state"] if completeness is not None else None
                ),
                "upstream_total": (
                    completeness.get("upstream_total")
                    if completeness is not None
                    else None
                ),
                "pages_fetched": (
                    completeness["pages_fetched"] if completeness is not None else 0
                ),
                "last_cursor": (
                    completeness.get("last_cursor")
                    if completeness is not None
                    else None
                ),
                "exhaustion_evidence": (
                    completeness.get("exhaustion_evidence")
                    if completeness is not None
                    else None
                ),
                "truncation_reason": (
                    completeness.get("truncation_reason")
                    if completeness is not None
                    else None
                ),
                "normalized_record_bytes_in_bundle": sum(
                    len(item["content"].encode())
                    for item in execution["source_record_items"]
                ),
                "elapsed_seconds": execution["elapsed_seconds"],
                "effective_product_record_limit": constraints["limit"],
                "effective_product_max_pages": retrieval["max_pages"],
                "effective_product_max_elapsed_seconds": retrieval[
                    "max_elapsed_seconds"
                ],
                "effective_product_max_normalized_bytes": retrieval["max_bytes"],
                "warning_count": len(execution["warnings"]),
                "warnings_json": canonical_json(execution["warnings"]),
                "failure_type": execution["failure_type"],
                "message": execution["message"],
            }
        )
    return rows


def _record_completeness_assessment(
    execution: dict[str, Any],
    bundle: dict[str, Any],
    run_capacity: dict[str, Any],
) -> dict[str, Any]:
    completeness = execution["record_completeness"]
    if execution["execution_status"] == "failed":
        return {
            "classification": "failed_execution_preserved",
            "closure_supported": False,
            "budget_stop_supported": None,
            "independently_reconstructable": True,
            "basis": execution["reason_code"],
            "judgment": "The route was executed and failed; it is neither empty nor complete.",
        }
    if completeness is None:
        raise ValueError("successful record-set execution lacks RecordCompleteness")
    state = completeness["state"]
    if state == "complete":
        returned = completeness["returned_count"]
        upstream_total = completeness.get("upstream_total")
        exhaustion_evidence = completeness.get("exhaustion_evidence")
        reconciles_total = upstream_total is None or returned == upstream_total
        closure_supported = bool(exhaustion_evidence) and reconciles_total
        return {
            "classification": (
                "verified_empty"
                if execution["record_result"] == "empty"
                else "complete"
            ),
            "closure_supported": closure_supported,
            "budget_stop_supported": None,
            "independently_reconstructable": True,
            "basis": exhaustion_evidence,
            "judgment": (
                "Closure is supported by explicit exhaustion evidence and any known upstream total reconciles with returned_count."
                if closure_supported
                else "The stored closure fields do not support a complete or empty claim."
            ),
        }
    if state == "upstream_total_unknown":
        unknown_is_preserved = (
            completeness.get("upstream_total") is None
            and completeness.get("exhaustion_evidence") is None
        )
        return {
            "classification": "upstream_total_unknown_preserved",
            "closure_supported": False,
            "budget_stop_supported": None,
            "independently_reconstructable": True,
            "basis": "No proven upstream total or exhaustion evidence is stored.",
            "judgment": (
                "Unknown completeness is validly preserved and is not treated as empty or complete."
                if unknown_is_preserved
                else "The unknown-completeness fields are internally inconsistent."
            ),
        }

    reason = completeness.get("truncation_reason")
    constraints = execution["operational_constraints"]
    retrieval = constraints["retrieval"]
    bundle_source_record_count = len(_bundle_items(bundle, "source_record"))
    normalized_bytes = sum(
        len(item["content"].encode()) for item in execution["source_record_items"]
    )
    exact_budget_checks: dict[str, bool] = {
        "max_records_reached": completeness["returned_count"] >= constraints["limit"],
        "max_pages_reached": completeness["pages_fetched"] >= retrieval["max_pages"],
        "max_elapsed_seconds_reached": execution["elapsed_seconds"]
        >= retrieval["max_elapsed_seconds"],
        "evidence_bundle_source_record_capacity_reached": bundle_source_record_count
        >= run_capacity["max_source_records"],
    }
    if reason in exact_budget_checks:
        supported = exact_budget_checks[reason]
        return {
            "classification": "truncated_at_declared_budget",
            "closure_supported": False,
            "budget_stop_supported": supported,
            "independently_reconstructable": True,
            "basis": reason,
            "judgment": (
                "The stored counter reaches the declared stop represented by truncation_reason."
                if supported
                else "The stored counters do not independently confirm the declared stop."
            ),
        }
    if reason == "max_bytes_reached":
        return {
            "classification": "truncated_at_normalized_byte_budget",
            "closure_supported": False,
            "budget_stop_supported": normalized_bytes < retrieval["max_bytes"],
            "independently_reconstructable": False,
            "basis": reason,
            "judgment": "The admitted prefix remains below the byte ceiling; the rejected next record is intentionally absent, so the exact crossing cannot be reconstructed from the Bundle alone.",
        }
    if reason == "evidence_bundle_byte_capacity_reached":
        return {
            "classification": "truncated_at_bundle_byte_budget",
            "closure_supported": False,
            "budget_stop_supported": len(canonical_bytes(bundle))
            <= run_capacity["max_bundle_canonical_bytes"],
            "independently_reconstructable": False,
            "basis": reason,
            "judgment": "The final Bundle remains within its byte ceiling; the rejected next item is absent, so the exact crossing cannot be reconstructed from the Bundle alone.",
        }
    return {
        "classification": "truncated_with_typed_stop",
        "closure_supported": False,
        "budget_stop_supported": bool(reason),
        "independently_reconstructable": False,
        "basis": reason,
        "judgment": "The typed truncation is preserved, but this audit has no counter rule for its exact stop reason.",
    }


def _source_completeness_review(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for result in results:
        seen_attempt_ids: set[str] = set()
        for capsule in result["evidence_bundles"]:
            bundle = capsule["evidence_bundle"]
            run_capacity = capsule["run_capacity"]
            for execution in _bundle_execution_rows(bundle):
                if execution["record_result"] is None:
                    continue
                if execution["attempt_id"] in seen_attempt_ids:
                    continue
                seen_attempt_ids.add(execution["attempt_id"])
                completeness = execution["record_completeness"] or {}
                rows.append(
                    {
                        "case_name": result["case_name"],
                        "attempt_id": execution["attempt_id"],
                        "bundle_role": capsule["bundle_role"],
                        "bundle_id": bundle["bundle_id"],
                        "qualified_source_route": execution["qualified_source"],
                        "operation": execution["operation"],
                        "execution_status": execution["execution_status"],
                        "record_result": execution["record_result"],
                        "record_completeness_state": completeness.get("state"),
                        "returned_count": completeness.get("returned_count"),
                        "output_item_count": len(execution["output_items"]),
                        "source_record_item_count": execution["source_record_count"],
                        "upstream_total": completeness.get("upstream_total"),
                        "pages_fetched": completeness.get("pages_fetched"),
                        "exhaustion_evidence": completeness.get("exhaustion_evidence"),
                        "truncation_reason": completeness.get("truncation_reason"),
                        "elapsed_seconds": execution["elapsed_seconds"],
                        "reason_code": execution["reason_code"],
                        "failure_type": execution["failure_type"],
                        "message": execution["message"],
                        "warnings": execution["warnings"],
                        "bundle_source_record_count": len(
                            _bundle_items(bundle, "source_record")
                        ),
                        "bundle_evidence_item_count": len(bundle["evidence_items"]),
                        "bundle_execution_count": len(bundle["executions"]),
                        "bundle_canonical_bytes": len(canonical_bytes(bundle)),
                        "effective_product_run_capacity": run_capacity,
                        "effective_product_record_limit": execution[
                            "operational_constraints"
                        ]["limit"],
                        "effective_product_max_pages": execution[
                            "operational_constraints"
                        ]["retrieval"]["max_pages"],
                        "effective_product_max_elapsed_seconds": execution[
                            "operational_constraints"
                        ]["retrieval"]["max_elapsed_seconds"],
                        "effective_product_max_normalized_bytes": execution[
                            "operational_constraints"
                        ]["retrieval"]["max_bytes"],
                        "assessment": _record_completeness_assessment(
                            execution, bundle, run_capacity
                        ),
                    }
                )
    return {
        "schema_version": "matrouter.paper-source-completeness-review/1",
        "semantics": "Deterministic internal review of each unique record-result-bearing case-ledger attempt at its first Bundle materialization. It keeps cumulative Bundle reassembly from double-counting attempts, preserves the independent execution_status, RecordCompleteness, and derived record_result axes, and is not an external scientific review.",
        "row_count": len(rows),
        "classification_counts": dict(
            sorted(Counter(row["assessment"]["classification"] for row in rows).items())
        ),
        "rows": rows,
    }


def _rq1_rq2_shared_ledger_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for result in results:
        primary = _primary_aggregate_bundle(result)
        executions = {
            row["qualified_source"]: row for row in _bundle_execution_rows(primary)
        }
        route_rows: list[dict[str, Any]] = []
        for route in sorted(primary["routes"], key=lambda row: row["qualified_source"]):
            source = route["qualified_source"]
            execution = executions.get(source)
            route_rows.append(
                {
                    "qualified_source_route": source,
                    "route_state": _route_state(route),
                    "shared_execution_attempt_id": (
                        execution["attempt_id"] if execution is not None else None
                    ),
                    "rq1_route_closure_view": (
                        None
                        if execution is None
                        else {
                            "attempted": True,
                            "execution_status": execution["execution_status"],
                            "record_result": execution["record_result"],
                            "returned_count": execution["returned_count"],
                            "record_completeness": execution["record_completeness"],
                        }
                    ),
                    "rq2_source_contribution_view": (
                        None
                        if execution is None
                        else {
                            "source_record_count": execution["source_record_count"],
                            "source_record_item_ids": [
                                item["item_id"]
                                for item in execution["source_record_items"]
                            ],
                        }
                    ),
                    "analysis_invariant": "Both views reference this one route execution; RQ2 performs no acquisition.",
                }
            )
        aggregate = result["aggregate"]
        shared = result["shared_discovery_ledger"]
        cases.append(
            {
                "case_name": result["case_name"],
                "authoritative_bundle_id": primary["bundle_id"],
                "aggregate_source_records_call_count": shared[
                    "aggregate_source_records_call_count"
                ],
                "additional_source_record_acquisition_count": shared[
                    "additional_source_record_acquisition_count"
                ],
                "rq1_qualified_route_count": aggregate["qualified_route_count"],
                "rq1_ready_route_count": aggregate["ready_route_count"],
                "rq1_attempted_route_count": aggregate["attempted_route_count"],
                "shared_discovery_source_record_count": aggregate[
                    "source_record_count"
                ],
                "rq2_contributing_exact_sources": shared["source_record_sources"],
                "invariants": {
                    "rq1_rq2_same_bundle": shared["rq1_rq2_same_bundle"],
                    "rq1_rq2_same_executions": True,
                    "rq1_rq2_same_source_record_items": True,
                    "separate_rq2_retrieval_count": 0,
                },
                "count_semantics": "There is one discovery record total per case. RQ1 reports coverage, execution, and closure; RQ2 reports source contribution and material context from those same records.",
                "routes": route_rows,
            }
        )
    return {
        "schema_version": "matrouter.paper-rq1-rq2-shared-ledger-audit/1",
        "protocol_version": PROTOCOL_VERSION,
        "semantics": "This audit proves shared identity; it does not compare two retrievals because no second RQ2 acquisition exists.",
        "case_count": len(cases),
        "cases": cases,
    }


def _provider_database_scope(qualified_source_route: str) -> str:
    if qualified_source_route.startswith("materialsgalaxy:"):
        return "materialsgalaxy"
    if qualified_source_route.startswith("optimade:"):
        endpoint = qualified_source_route.removeprefix("optimade:").split("/", 1)[0]
        return f"optimade:{endpoint}"
    return qualified_source_route


def _portable_method_result(value: dict[str, Any]) -> dict[str, Any]:
    """Remove machine-specific prefixes while retaining content identities and hashes."""
    copied = json.loads(json.dumps(value))

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, child in tuple(node.items()):
                if key in {"path", "output_path", "output_directory"} and isinstance(
                    child, str
                ):
                    target = (
                        ARTIFACTS
                        if key == "output_directory"
                        else ARTIFACTS / Path(child).name
                    )
                    node[key] = str(target.relative_to(REPOSITORY_ROOT))
                else:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(copied)
    return copied


def _compute_lifepo4_phase_diagram(bundle_model: Any) -> dict[str, Any] | None:
    from matrouter.evidence_contracts import ScientificArtifactItem
    from matrouter.phase_diagram import (
        PhaseDiagramDataset,
        PhaseDiagramMethodParameters,
        PhaseDiagramPlotParameters,
        PhaseDiagramRequest,
        compute_phase_diagrams,
    )

    bundle = bundle_model.model_dump(mode="json", exclude_computed_fields=True)
    thermo_executions = [
        row
        for row in _bundle_execution_rows(bundle)
        if row["operation"] == "get_thermochemical_entries"
    ]
    if len(thermo_executions) != 1:
        return None
    execution = thermo_executions[0]
    completeness = execution.get("record_completeness") or {}
    if (
        execution["execution_status"] != "succeeded"
        or completeness.get("state") != "complete"
    ):
        return None
    entry_sets = [
        item
        for item in bundle_model.evidence_items
        if isinstance(item, ScientificArtifactItem)
        and item.artifact_type == "thermochemical_entry_set"
    ]
    if len(entry_sets) != 1:
        return None
    entry_set = entry_sets[0]
    entry_payload = entry_set.scientific_payload()
    entries = entry_payload.get("entries") if isinstance(entry_payload, dict) else None
    if (
        entry_set.identity.source != "materials_project"
        or not isinstance(entries, list)
        or len(entries) < 2
    ):
        return None
    request = PhaseDiagramRequest(
        datasets=(
            PhaseDiagramDataset(
                label=f"materials-project-{THERMO_TYPE}",
                chemical_system=("Fe", "Li", "O", "P"),
                entry_set=entry_set,
            ),
        ),
        method_parameters=PhaseDiagramMethodParameters(
            on_hull_tolerance_eV_per_atom=ON_HULL_TOLERANCE_EV_PER_ATOM
        ),
        plot=PhaseDiagramPlotParameters(
            output_directory=str(ARTIFACTS),
            image_format="svg",
            show_unstable_eV_per_atom=0.2,
            label_pymatgen_stable_representatives=True,
            label_unstable=False,
            ternary_style="2d",
            dpi=150,
        ),
    )
    result = compute_phase_diagrams(request)
    return {
        "method_name": "compute_phase_diagrams",
        "input_bundle_id": bundle_model.bundle_id,
        "exact_input_item_ids": [entry_set.item_id],
        "request": request.model_dump(mode="json", exclude_computed_fields=True),
        "result": result.model_dump(mode="json", exclude_computed_fields=True),
    }


def _match_preregistered_mos2_structures(
    bundle_capsules: list[dict[str, Any]], spec: dict[str, Any]
) -> dict[str, Any] | None:
    from matrouter.evidence_contracts import StructureItem
    from matrouter.structure_matching import (
        ReferencedStructure,
        StructureMatcherParameters,
        StructureMatchRequest,
        match_structures,
    )

    method_spec = spec["explicit_structure_method"]
    selected: list[tuple[str, StructureItem]] = []
    for target_name in ("first", "second"):
        target = method_spec[target_name]
        matches_by_item_id = {
            item["item_id"]: (
                capsule["evidence_bundle"]["bundle_id"],
                StructureItem.model_validate(wire(item)),
            )
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "target_followup"
            for item in capsule["evidence_bundle"]["evidence_items"]
            if item["item_kind"] == "structure"
            and item["identity"]["source"] == target["qualified_source_route"]
            and item["identity"]["source_id"] == target["source_id"]
        }
        if len(matches_by_item_id) != 1:
            return None
        selected.append(next(iter(matches_by_item_id.values())))
    parameters = StructureMatcherParameters(**method_spec["parameters"])
    request = StructureMatchRequest(
        first=ReferencedStructure(item=selected[0][1]),
        second=ReferencedStructure(item=selected[1][1]),
        parameters=parameters,
    )
    method_result = match_structures(request)
    return {
        "method_name": "match_structures",
        "input_bundle_ids": [selected[0][0], selected[1][0]],
        "exact_input_item_ids": [selected[0][1].item_id, selected[1][1].item_id],
        "request": request.model_dump(mode="json", exclude_computed_fields=True),
        "result": method_result.model_dump(mode="json", exclude_computed_fields=True),
        "interpretation_limit": method_spec["interpretation_limit"],
    }


def _render_spectral_methods(case_name: str, bundle_model: Any) -> list[dict[str, Any]]:
    from matrouter.evidence_contracts import ScientificArtifactItem
    from matrouter.spectral_rendering import (
        BandStructureRenderParameters,
        BandStructureRenderRequest,
        DensityOfStatesRenderParameters,
        DensityOfStatesRenderRequest,
        ReferencedSpectralArtifact,
        render_band_structure,
        render_density_of_states,
    )

    methods: list[dict[str, Any]] = []
    for item in bundle_model.evidence_items:
        if not isinstance(item, ScientificArtifactItem):
            continue
        source_label = _safe_label(f"{item.identity.source}-{item.identity.source_id}")[
            :100
        ]
        if item.artifact_type == "band_structure":
            request = BandStructureRenderRequest(
                artifact=ReferencedSpectralArtifact(item=item),
                parameters=BandStructureRenderParameters(
                    output_path=str(ARTIFACTS / f"{case_name}-{source_label}-band.svg"),
                    image_format="svg",
                    title=f"{case_name}: {item.identity.source} band structure",
                    ylim=(-8.0, 8.0),
                ),
            )
            result = render_band_structure(request)
            method_name = "render_band_structure"
        elif item.artifact_type == "density_of_states":
            request = DensityOfStatesRenderRequest(
                artifact=ReferencedSpectralArtifact(item=item),
                parameters=DensityOfStatesRenderParameters(
                    output_path=str(ARTIFACTS / f"{case_name}-{source_label}-dos.svg"),
                    image_format="svg",
                    title=f"{case_name}: {item.identity.source} density of states",
                    xlim=(-8.0, 8.0),
                    ylim=None,
                    orbital_projection_keys=(),
                ),
            )
            result = render_density_of_states(request)
            method_name = "render_density_of_states"
        else:
            continue
        methods.append(
            _portable_method_result(
                {
                    "method_name": method_name,
                    "input_bundle_id": bundle_model.bundle_id,
                    "exact_input_item_ids": [item.item_id],
                    "request": request.model_dump(
                        mode="json", exclude_computed_fields=True
                    ),
                    "result": result.model_dump(mode="json"),
                    "portability_transform": "Only filesystem path strings were made repository-relative; input and output content IDs and hashes are unchanged.",
                }
            )
        )
    return methods


def _derive_explicit_methods(
    case_name: str,
    bundle_capsules: list[dict[str, Any]],
    spec: dict[str, Any],
    existing_methods: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Run preregistered local methods over exact items in captured Bundles."""
    from matrouter.evidence_contracts import EvidenceBundle

    methods = [_portable_method_result(method) for method in (existing_methods or [])]
    method_names = [method.get("method_name") for method in methods]
    if len(method_names) != len(set(method_names)):
        raise ValueError(f"{case_name}: duplicate explicit method result")
    if case_name == "mos2-band-gap":
        spectral_capsules = [
            capsule
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "target_followup"
            and capsule["qualified_source_route"] == "materials_project"
        ]
        missing_spectral_methods = {
            "render_band_structure",
            "render_density_of_states",
        } - set(method_names)
        if missing_spectral_methods and len(spectral_capsules) == 1:
            bundle_model = EvidenceBundle.model_validate(
                wire(spectral_capsules[0]["evidence_bundle"])
            )
            methods.extend(
                method
                for method in _render_spectral_methods(case_name, bundle_model)
                if method["method_name"] in missing_spectral_methods
            )
        if "match_structures" not in method_names:
            structure_match = _match_preregistered_mos2_structures(
                bundle_capsules, spec
            )
            if structure_match is not None:
                methods.append(structure_match)
    elif case_name == "lifepo4-stability":
        thermo_capsules = [
            capsule
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "thermochemical"
        ]
        if "compute_phase_diagrams" not in method_names and len(thermo_capsules) == 1:
            bundle_model = EvidenceBundle.model_validate(
                wire(thermo_capsules[0]["evidence_bundle"])
            )
            phase_result = _compute_lifepo4_phase_diagram(bundle_model)
            if phase_result is not None:
                methods.append(_portable_method_result(phase_result))
    return methods


def _interpretation(
    result: dict[str, Any],
    spec: dict[str, Any],
    coverage: list[dict[str, Any]],
    methods: list[dict[str, Any]],
) -> dict[str, Any]:
    scientific_rows = _paper_scientific_rows(result)
    observations = scientific_rows["observations"]
    aggregate = result["aggregate"]
    explicitly_experimental_band_gaps = [
        observation
        for observation in observations
        if observation["property"] == "band_gap_eV"
        and str(json.loads(observation["context_json"]).get("modality")).lower()
        in {"experiment", "experimental"}
    ]
    entry_sets = [
        item
        for item in _case_items(result, "scientific_artifact")
        if item["artifact_type"] == "thermochemical_entry_set"
    ]
    return {
        "retrieved_facts": {
            "qualified_route_count": aggregate["qualified_route_count"],
            "attempted_route_count": aggregate["attempted_route_count"],
            "aggregate_bundle_id": aggregate["bundle_id"],
            "aggregate_source_record_count": aggregate["source_record_count"],
            "aggregate_distinct_source_count": aggregate["source_record_source_count"],
            "aggregate_distinct_provider_count": aggregate[
                "source_record_provider_count"
            ],
            "aggregate_execution_status_counts": aggregate["execution_status_counts"],
            "aggregate_record_result_counts": aggregate["record_result_counts"],
            "aggregate_completeness_counts": aggregate["record_completeness_counts"],
            "shared_discovery_ledger": result["shared_discovery_ledger"],
            "exact_target_audit": result["protocol_conformance"][
                "stage_2_target_audit"
            ],
            "exact_target_artifacts": scientific_rows["artifacts"],
            "explicit_method_names": [row["method_name"] for row in methods],
            "thermochemical_entry_count": sum(
                _thermochemical_entry_count(item) for item in entry_sets
            ),
            "explicitly_identified_experimental_band_gap_observation_count": len(
                explicitly_experimental_band_gaps
            ),
            "qualified_source_route_count_semantics": QUALIFIED_ROUTE_COUNT_SEMANTICS,
        },
        "stage_1_scope": STAGE_1_SCOPE,
        "shared_discovery_scope": SHARED_DISCOVERY_SCOPE,
        "context_differences": spec["context_differences"],
        "allowed_statement": spec["allowed_statement"],
        "prohibited_statement": spec["prohibited_statement"],
        "missing_evidence": spec["missing_evidence"],
        "next_action": spec["next_action"],
    }


def _phase_diagram_export_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    methods = [
        method
        for method in result["explicit_methods"]
        if method.get("method_name") == "compute_phase_diagrams"
        and _method_result_succeeded(method)
    ]
    if len(methods) != 1:
        return []
    method = methods[0]
    entry_sets = _complete_thermochemical_entry_sets(result)
    if len(entry_sets) != 1:
        return []
    entry_set = entry_sets[0]
    entry_set_payload = _artifact_content(entry_set)
    context = entry_set_payload["thermochemical_context"]
    energy_frame = context["energy_frame"]
    dataset_result = method["result"]["datasets"][0]
    tolerance = method["result"]["method_parameters"]["on_hull_tolerance_eV_per_atom"]
    return [
        {
            "case_name": result["case_name"],
            "source": entry["reference"]["source"],
            "source_id": entry["reference"]["source_id"],
            "entry_set_item_id": entry_set["item_id"],
            "entry_set_source_id": entry_set["identity"]["source_id"],
            "input_manifest_id": dataset_result["input_manifest"]["manifest_id"],
            "dataset": context["dataset"],
            "materials_project_database_snapshot": context["input_versions"][
                "materials_project_database"
            ],
            "thermo_type": context["thermo_types"][0],
            "energy_frame_id": energy_frame["frame_id"],
            "energy_frame_description": "Materials Project GGA/GGA+U/r2SCAN compatibility-mixed frame; not a single functional or one homogeneous DFT method.",
            "composition_json": canonical_json(entry["composition"]),
            "corrected_energy_eV": entry["corrected_energy_eV"],
            "formation_energy_eV_per_atom": entry["formation_energy_eV_per_atom"],
            "energy_above_hull_eV_per_atom": entry["energy_above_hull_eV_per_atom"],
            "on_hull_within_tolerance": entry["on_hull_within_tolerance"],
            "on_hull_tolerance_eV_per_atom": tolerance,
            "tolerance_semantics": "Numerical on-hull classification tolerance; not DFT uncertainty, physical accuracy, or a confidence interval.",
            "scope_limitation": "Result is limited to this exact Materials Project entry set, compatibility-mixed frame, and dataset snapshot; it does not establish finite-temperature or universal stability or synthesizability.",
        }
        for entry in dataset_result["entries"]
    ]


def _topology_soc_comparison_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _case_items(result, "scientific_artifact"):
        if item["artifact_type"] not in {"topology_no_soc", "topology_soc"}:
            continue
        descriptor = _artifact_content(item)
        structure_identity = descriptor["source_native_structure_identity"]
        rows.append(
            {
                "case_name": result["case_name"],
                "source": item["identity"]["source"],
                "source_id": item["identity"]["source_id"],
                "formula": descriptor["data"]["reduced_formula"],
                "source_native_space_group_symbol": structure_identity["symbol"],
                "source_native_space_group_number": structure_identity["number"],
                "soc": descriptor["soc"],
                "materials_galaxy_reported_topology_class": descriptor[
                    "source_native_topo_class"
                ],
                "source_native_indicators_json": canonical_json(
                    descriptor.get("source_native_indicators") or {}
                ),
                "artifact_item_id": item["item_id"],
                "content_sha256": sha256_bytes(item["content"].encode()),
                "evidence_semantics": "Deterministic descriptive view of the same source-native Bundle artifact; not new evidence or independent topology validation.",
                "method_limitation": "MaterialsGalaxy reports this classification; MatRouter did not recompute topology invariants or surface states.",
                "phase_equivalence_status": "Not assessed in the Bi2Se3 case; that case executed no explicit cross-source structure matching.",
            }
        )
    return sorted(rows, key=lambda row: (row["source_id"], row["soc"]))


def _paper_highlights(result: dict[str, Any]) -> dict[str, Any]:
    case_name = result["case_name"]
    if case_name == "mos2-band-gap":
        match_methods = [
            method
            for method in result["explicit_methods"]
            if method.get("method_name") == "match_structures"
            and _method_result_succeeded(method)
        ]
        return {
            "result_scope": "capacity_bounded_multi_source_structure_and_electronic_landscape_not_phase_resolved_gap_answer",
            "explicitly_identified_experimental_band_gap_observation_count": result[
                "case_interpretation"
            ]["retrieved_facts"][
                "explicitly_identified_experimental_band_gap_observation_count"
            ],
            "explicit_structure_matching_performed": len(match_methods) == 1,
            "explicit_structure_match": (
                None
                if len(match_methods) != 1
                else {
                    "first": result["task_spec"]["explicit_structure_method"]["first"],
                    "second": result["task_spec"]["explicit_structure_method"][
                        "second"
                    ],
                    "matched": match_methods[0]["result"]["matched"],
                    "parameters": match_methods[0]["result"]["parameters"],
                    "distance_status": match_methods[0]["result"]["distance_status"],
                    "interpretation_limit": match_methods[0]["interpretation_limit"],
                }
            ),
            "spectral_render_semantics": "Derived views of exact Bundle artifacts; no additional source evidence.",
        }
    if case_name == "lifepo4-stability":
        phase_rows = _phase_diagram_export_rows(result)
        first = phase_rows[0] if phase_rows else None
        return {
            "phase_diagram_entry_count": len(phase_rows),
            "materials_project_database_snapshot": None
            if first is None
            else first["materials_project_database_snapshot"],
            "thermo_type": None if first is None else first["thermo_type"],
            "energy_frame_description": None
            if first is None
            else first["energy_frame_description"],
            "on_hull_tolerance_eV_per_atom": None
            if first is None
            else first["on_hull_tolerance_eV_per_atom"],
            "tolerance_semantics": None
            if first is None
            else first["tolerance_semantics"],
            "continuous_energy_above_hull_export": "results/phase-diagram-entries.csv",
        }
    if case_name == "bi2se3-topology":
        return {
            "comparison_semantics": "MaterialsGalaxy-reported same-formula phase by SOC descriptive table; not new evidence.",
            "explicit_structure_matching_performed": False,
            "rows": [
                {
                    key: row[key]
                    for key in (
                        "source",
                        "source_id",
                        "source_native_space_group_symbol",
                        "source_native_space_group_number",
                        "soc",
                        "materials_galaxy_reported_topology_class",
                    )
                }
                for row in _topology_soc_comparison_rows(result)
            ],
        }
    raise ValueError(f"unknown case: {case_name}")


def _capability_audit(capability: Any) -> dict[str, Any]:
    document = json.loads(capability.capability_document_json)
    readiness = document["evidence_route_readiness"]
    catalog_sources = document["source_catalog"]["sources"]
    optimade = next(row for row in catalog_sources if row["name"] == "optimade")
    children = [row["name"] for row in optimade.get("children", [])]
    credential_sources = {
        row["source"]: row.get("api_key", {}).get("configured")
        for row in readiness["sources"]
        if row["source"]
        in {
            "materials_project",
            "mpds",
            "materialsgalaxy:topo_crystals",
        }
    }
    audit = {
        "matrouter_optimade_providers_is_wildcard": os.environ.get(
            "MATROUTER_OPTIMADE_PROVIDERS"
        )
        == "*",
        "credentialed_provider_configuration": {
            "materials_project": credential_sources.get("materials_project") is True,
            "mpds": credential_sources.get("mpds") is True,
            "materialsgalaxy": credential_sources.get("materialsgalaxy:topo_crystals")
            is True,
        },
        "declared_source_authority_count": readiness["summary"]["source_count"],
        "ready_pair_count": readiness["summary"]["ready_pair_count"],
        "requires_configuration_pair_count": readiness["summary"][
            "requires_configuration_pair_count"
        ],
        "optimade_child_route_count": len(children),
        "optimade_child_routes": children,
        "optimade_exclusions": OPTIMADE_WILDCARD_EXCLUSIONS,
        "optimade_provider_warnings": optimade.get("warnings", []),
    }
    if not audit["matrouter_optimade_providers_is_wildcard"]:
        raise ValueError("MATROUTER_OPTIMADE_PROVIDERS must be '*' for the final run")
    if not all(audit["credentialed_provider_configuration"].values()):
        raise ValueError("MP, MPDS, and MaterialsGalaxy must all be configured")
    if not audit["optimade_child_routes"]:
        raise RuntimeError("OPTIMADE wildcard expansion returned no usable child route")
    return audit


def _serialized_run(
    *,
    run_role: str,
    qualified_source_route: str | None,
    run: Any,
    requirements: list[Any],
    routes: list[Any],
    acquisitions: list[Any],
) -> dict[str, Any]:
    return {
        "run_role": run_role,
        "qualified_source_route": qualified_source_route,
        "run_capacity": run.capacity.model_dump(mode="json"),
        "requirements": [row.model_dump(mode="json") for row in requirements],
        "routes": [row.model_dump(mode="json") for row in routes],
        "acquisitions": [row.model_dump(mode="json") for row in acquisitions],
    }


def _assemble_run(
    tools: Any, run_id: str, requirements: list[Any], acquisitions: list[Any]
) -> Any:
    from matrouter.tools.evidence import AssembleEvidenceBundleRequest

    return tools.assemble_evidence_bundle(
        AssembleEvidenceBundleRequest(
            evidence_run_id=run_id,
            requirement_ids=tuple(
                sorted({requirement.requirement_id for requirement in requirements})
            ),
            acquisition_ids=tuple(
                sorted({acquisition.acquisition_id for acquisition in acquisitions})
            ),
        )
    )


def _shared_discovery_summary(
    primary_bundle: dict[str, Any], run_capacity: dict[str, Any]
) -> dict[str, Any]:
    from matrouter.evidence_contracts import SourceRecordItem

    ready_routes = sorted(
        route["qualified_source"]
        for route in primary_bundle["routes"]
        if _route_is_ready(route) and route["operation"] == "search_materials"
    )
    executions = _bundle_execution_rows(primary_bundle)
    record_items = _bundle_items(primary_bundle, "source_record")
    record_identities = [
        SourceRecordItem.model_validate(wire(item)).identity for item in record_items
    ]
    gaps = []
    for execution in executions:
        completeness = execution.get("record_completeness") or {}
        if execution["record_result"] in {"complete", "empty"}:
            continue
        gaps.append(
            {
                "source": execution["qualified_source"],
                "execution_status": execution["execution_status"],
                "record_result": execution["record_result"],
                "record_completeness": completeness.get("state"),
                "record_count": execution["source_record_count"],
                "upstream_total": completeness.get("upstream_total"),
                "reason_code": execution["reason_code"],
                "truncation_reason": completeness.get("truncation_reason"),
                "warnings": execution["warnings"],
            }
        )
    attempted_routes = sorted(row["qualified_source"] for row in executions)
    source_record_requirements = [
        requirement
        for requirement in primary_bundle["requirements"]
        if requirement["evidence_kind"] == "source_record"
    ]
    if len(source_record_requirements) != 1:
        raise ValueError(
            "authoritative discovery Bundle must have one source-record requirement"
        )
    return {
        "semantics": "RQ1 route execution/closure and RQ2 source contribution/material landscape are deterministic views of this one authoritative all-qualified aggregate Bundle. No additional source-record acquisition contributes to either view.",
        "authoritative_bundle_id": primary_bundle["bundle_id"],
        "rq1_rq2_same_bundle": True,
        "aggregate_source_records_call_count": 1,
        "additional_source_record_acquisition_count": 0,
        "ready_route_count": len(ready_routes),
        "attempted_route_count": len(attempted_routes),
        "all_ready_routes_attempted": attempted_routes == ready_routes,
        "source_record_count": len(record_items),
        "source_record_item_count": len(record_items),
        "source_record_sources": sorted(
            {identity.source for identity in record_identities}
        ),
        "source_record_providers": sorted(
            {identity.provider for identity in record_identities}
        ),
        "execution_status_counts": dict(
            sorted(Counter(row["execution_status"] for row in executions).items())
        ),
        "record_result_counts": dict(
            sorted(Counter(row["record_result"] for row in executions).items())
        ),
        "record_completeness_counts": dict(
            sorted(
                Counter(
                    row["record_completeness"]["state"]
                    for row in executions
                    if row["record_completeness"] is not None
                ).items()
            )
        ),
        "complete_inventory_eligible": attempted_routes == ready_routes and not gaps,
        "gap_count": len(gaps),
        "gaps": gaps,
        "effective_operational_constraints": source_record_requirements[0][
            "operational_constraints"
        ],
        "effective_product_run_capacity": run_capacity,
    }


def acquire_authoritative_discovery(
    router: Any,
    *,
    case_name: str,
    formula: str,
) -> dict[str, Any]:
    """Acquire the one authoritative discovery Bundle shared by RQ1 and RQ2."""
    from matrouter.tools.evidence import (
        AggregateSourceRecordsRequest,
        BeginEvidenceRunRequest,
        EvidenceTools,
    )
    from matrouter.tools.run_state import SessionRunRegistry

    registry = SessionRunRegistry()
    primary_tools = EvidenceTools(router, registry)
    primary_run = primary_tools.begin_evidence_run(BeginEvidenceRunRequest())
    discovery = _create_requirement(
        primary_tools,
        primary_run.evidence_run_id,
        subject=_subject(formula=formula),
        kind="source_record",
        constraints=_constraints(all_qualified=True),
    )
    primary_bundle_model = primary_tools.aggregate_source_records(
        AggregateSourceRecordsRequest(
            evidence_run_id=primary_run.evidence_run_id,
            requirements=(discovery,),
        )
    )
    primary_bundle = primary_bundle_model.model_dump(
        mode="json", exclude_computed_fields=True
    )
    primary_routes = sorted(
        primary_bundle_model.routes,
        key=lambda row: row.qualified_source,
    )
    qualified_sources = [row.qualified_source for row in primary_routes]
    if len(qualified_sources) != len(set(qualified_sources)):
        raise ValueError("all-qualified catalog contains duplicate exact routes")
    discovery_acquisitions = _registered_acquisitions(
        registry,
        primary_run.evidence_run_id,
        requirement_ids={discovery.requirement_id},
    )
    if any(row.route.operation != "search_materials" for row in discovery_acquisitions):
        raise ValueError(
            "authoritative discovery ledger contains a non-search acquisition"
        )
    ready_route_count = sum(route.is_ready for route in primary_routes)
    if len(discovery_acquisitions) != ready_route_count:
        raise ValueError(
            f"{case_name}: aggregate acquisition count does not match ready route count"
        )
    raw_runs = [
        {
            "run_role": "primary_aggregate",
            "qualified_source_route": None,
            "run_capacity": primary_run.capacity.model_dump(mode="json"),
            "requirements": [discovery.model_dump(mode="json")],
            "routes": [route.model_dump(mode="json") for route in primary_routes],
            "acquisitions": [
                row.model_dump(mode="json") for row in discovery_acquisitions
            ],
            "canonical_bundle": primary_bundle,
        }
    ]
    bundle_capsules = [
        {
            "bundle_role": "primary_aggregate",
            "qualified_source_route": None,
            "run_capacity": primary_run.capacity.model_dump(mode="json"),
            "evidence_bundle": primary_bundle,
        }
    ]
    shared_summary = _shared_discovery_summary(
        primary_bundle, primary_run.capacity.model_dump(mode="json")
    )

    return {
        "tools": primary_tools,
        "registry": registry,
        "run": primary_run,
        "discovery_requirement": discovery,
        "discovery_acquisitions": discovery_acquisitions,
        "raw_runs": raw_runs,
        "bundle_capsules": bundle_capsules,
        "primary_bundle_model": primary_bundle_model,
        "primary_routes": primary_routes,
        "qualified_sources": qualified_sources,
        "primary_summary": _aggregate_summary(primary_bundle),
        "shared_discovery_summary": shared_summary,
        "aggregate_source_records_call_count": 1,
    }


def acquire_case(
    case_name: str,
    *,
    full_run_id: str,
    raw_output_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    from matrouter import create_router
    from matrouter.evidence_contracts import SourceFilter
    from matrouter.evidence_contracts import canonical_json as matrouter_canonical_json
    from matrouter.tools.evidence import CapabilityRequest, EvidenceTools
    from matrouter.tools.run_state import SessionRunRegistry

    spec = case_spec(case_name)
    case_started = time.monotonic()
    formula = spec["formula"]
    router = create_router()
    try:
        capability_tools = EvidenceTools(router, SessionRunRegistry())
        capability = capability_tools.inspect_evidence_capabilities(CapabilityRequest())
        capability_audit = _capability_audit(capability)
        discovery_ledger = acquire_authoritative_discovery(
            router,
            case_name=case_name,
            formula=formula,
        )
        case_tools = discovery_ledger["tools"]
        case_run = discovery_ledger["run"]
        case_run_id = case_run.evidence_run_id
        discovery_requirement = discovery_ledger["discovery_requirement"]
        discovery_acquisitions = discovery_ledger["discovery_acquisitions"]
        aggregate_bundle_model = discovery_ledger["primary_bundle_model"]
        qualified_sources = discovery_ledger["qualified_sources"]
        aggregate_bundle = aggregate_bundle_model.model_dump(
            mode="json", exclude_computed_fields=True
        )
        raw_runs = discovery_ledger["raw_runs"]
        bundle_capsules: list[dict[str, Any]] = discovery_ledger["bundle_capsules"]
        shared_discovery_summary = discovery_ledger["shared_discovery_summary"]
        coverage = _aggregate_coverage_rows(case_name, aggregate_bundle)
        methods: list[dict[str, Any]] = []
        case_requirements: list[Any] = [discovery_requirement]
        case_acquisitions: list[Any] = list(discovery_acquisitions)
        target_specs_by_source: dict[str, list[dict[str, Any]]] = {}
        for target in spec["stage_2_targets"]:
            if target["enrichment_routes"]:
                target_specs_by_source.setdefault(
                    target["qualified_source_route"], []
                ).append(target)

        for source_index, source in enumerate(sorted(target_specs_by_source)):
            print(
                f"[{case_name}] exact-target follow-up {source_index + 1}/{len(target_specs_by_source)}: {source}",
                flush=True,
            )
            requirements: list[Any] = []
            routes: list[Any] = []
            acquisitions: list[Any] = []
            exact_refs = _all_exact_refs(discovery_acquisitions)
            for target in target_specs_by_source[source]:
                matches = [
                    (upstream, record_ref)
                    for upstream, record_ref in exact_refs
                    if (record_ref.source, record_ref.source_id)
                    == (source, target["source_id"])
                ]
                if len(matches) != 1:
                    continue
                upstream, record_ref = matches[0]
                for route_spec in target["enrichment_routes"]:
                    _add_bound_detail(
                        tools=case_tools,
                        run_id=case_run_id,
                        case_name=case_name,
                        formula=formula,
                        source=record_ref.source,
                        kind=route_spec["evidence_kind"],
                        operation=route_spec["operation"],
                        discovery_acquisition=upstream,
                        record_ref=record_ref,
                        requirements=requirements,
                        routes=routes,
                        acquisitions=acquisitions,
                    )
            case_requirements.extend(requirements)
            case_acquisitions.extend(acquisitions)
            raw_runs.append(
                _serialized_run(
                    run_role="target_followup",
                    qualified_source_route=source,
                    run=case_run,
                    requirements=requirements,
                    routes=routes,
                    acquisitions=acquisitions,
                )
            )
            if acquisitions:
                target_bundle_model = _assemble_run(
                    case_tools,
                    case_run_id,
                    case_requirements,
                    case_acquisitions,
                )
                target_bundle = target_bundle_model.model_dump(
                    mode="json", exclude_computed_fields=True
                )
                bundle_capsules.append(
                    {
                        "bundle_role": "target_followup",
                        "qualified_source_route": source,
                        "run_capacity": case_run.capacity.model_dump(mode="json"),
                        "evidence_bundle": target_bundle,
                    }
                )
        if case_name == "lifepo4-stability":
            source_filter = SourceFilter(
                source="materials_project",
                filter_json=matrouter_canonical_json({"thermo_types": [THERMO_TYPE]}),
            )
            thermo = _create_requirement(
                case_tools,
                case_run_id,
                subject=_subject(elements=("Fe", "Li", "O", "P")),
                kind="thermochemical_entries",
                constraints=_constraints(
                    sources=("materials_project",),
                    filters=(source_filter,),
                ),
            )
            thermo_requirements = [thermo]
            thermo_routes = _route(case_tools, case_run_id, thermo)
            thermo_acquisitions: list[Any] = []
            for route in thermo_routes:
                if route.is_ready and route.operation == "get_thermochemical_entries":
                    thermo_acquisitions.append(
                        _execute(
                            case_tools,
                            case_run_id,
                            thermo,
                            route,
                            "paper-release-lifepo4-thermochemical-entries",
                        )
                    )
            case_requirements.extend(thermo_requirements)
            case_acquisitions.extend(thermo_acquisitions)
            thermo_bundle_model = _assemble_run(
                case_tools,
                case_run_id,
                case_requirements,
                case_acquisitions,
            )
            thermo_bundle = thermo_bundle_model.model_dump(
                mode="json", exclude_computed_fields=True
            )
            raw_runs.append(
                _serialized_run(
                    run_role="thermochemical",
                    qualified_source_route="materials_project",
                    run=case_run,
                    requirements=thermo_requirements,
                    routes=thermo_routes,
                    acquisitions=thermo_acquisitions,
                )
            )
            bundle_capsules.append(
                {
                    "bundle_role": "thermochemical",
                    "qualified_source_route": "materials_project",
                    "run_capacity": case_run.capacity.model_dump(mode="json"),
                    "evidence_bundle": thermo_bundle,
                }
            )
        methods = _derive_explicit_methods(case_name, bundle_capsules, spec)
    finally:
        router.close()

    case_elapsed_seconds = round(time.monotonic() - case_started, 3)
    raw_capture = {
        "schema_version": "matrouter.paper-live-capture/8",
        "full_run_id": full_run_id,
        "case_name": case_name,
        "protocol_version": PROTOCOL_VERSION,
        "release_binding": load_json(IDENTITY_PATH),
        "retrieval_strategy": {
            "stage_1": spec["stage_1"],
            "primary_aggregate": STAGE_1_SCOPE,
            "shared_discovery_policy": spec["shared_discovery_policy"],
            "shared_discovery_scope": SHARED_DISCOVERY_SCOPE,
            "stage_2_targets": spec["stage_2_targets"],
            "stage_2_selection_rule": "only exact targets preregistered before the live run and present in the authoritative aggregate may be enriched; every detail or artifact attempt binds its exact initial discovery acquisition and record reference, no prerequisite source search is issued, and no target is dynamically replaced",
            "qualified_source_routes": qualified_sources,
        },
        "evidence_run_count": 1,
        "aggregate_source_records_call_count": discovery_ledger[
            "aggregate_source_records_call_count"
        ],
        "qualified_source_routes": qualified_sources,
        "capability_audit": capability_audit,
        "capability_snapshot": capability.model_dump(mode="json"),
        "shared_discovery_ledger": shared_discovery_summary,
        "runs": raw_runs,
        "case_elapsed_seconds": case_elapsed_seconds,
    }
    if raw_output_path is not None:
        write_json(raw_output_path, raw_capture)
    _, protocol_conformance = _capture_protocol_status(raw_capture, spec)
    result = {
        "schema_version": "matrouter.paper-case-result/14",
        "full_run_id": full_run_id,
        "case_name": case_name,
        "protocol_version": PROTOCOL_VERSION,
        "research_questions": COMMON_RESEARCH_QUESTIONS,
        "shared_discovery_policy": SHARED_DISCOVERY_POLICY,
        "rq3_method_applicability": spec["rq3_method_applicability"],
        "scientific_question": spec["scientific_question"],
        "task_spec": spec,
        "actual_retrieval_strategy": raw_capture["retrieval_strategy"],
        "protocol_conformance": protocol_conformance,
        "coverage_matrix": coverage,
        "evidence_bundles": bundle_capsules,
        "primary_result_bundle_id": aggregate_bundle["bundle_id"],
        "aggregate": _aggregate_summary(aggregate_bundle),
        "shared_discovery_ledger": shared_discovery_summary,
        "explicit_methods": methods,
        "case_elapsed_seconds": case_elapsed_seconds,
    }
    result["material_landscape"] = _material_landscape_trace(result, spec)
    result["case_interpretation"] = _interpretation(result, spec, coverage, methods)
    result["unresolved_product_blockers"] = _diagnose_case_product_blockers(result)
    result["paper_results_eligible"] = _case_paper_eligible(result)
    result["paper_results_eligibility_semantics"] = PAPER_ELIGIBILITY_SEMANTICS
    result["paper_result_status"] = _paper_result_status(result)
    return raw_capture, result, coverage


def export_results(
    results: list[dict[str, Any]], coverage: list[dict[str, Any]]
) -> None:
    coverage_path = RESULTS / "coverage.csv"
    coverage_export = [
        {
            **{key: value for key, value in row.items() if key != "source"},
            "qualified_source_route": row["source"],
            "provider_database_scope": _provider_database_scope(row["source"]),
        }
        for row in coverage
    ]
    with coverage_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coverage_export[0]))
        writer.writeheader()
        writer.writerows(coverage_export)
    source_outcome_audit = [
        row for result in results for row in _source_outcome_audit_rows(result)
    ]
    with (RESULTS / "source-outcome-audit.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(source_outcome_audit[0]))
        writer.writeheader()
        writer.writerows(source_outcome_audit)
    write_json(
        RESULTS / "source-completeness-review.json",
        _source_completeness_review(results),
    )
    write_json(
        RESULTS / "rq1-rq2-shared-ledger-audit.json",
        _rq1_rq2_shared_ledger_report(results),
    )
    rows: list[dict[str, Any]] = []
    figure_cases: list[dict[str, Any]] = []
    scientific_exports: dict[str, list[dict[str, Any]]] = {
        "observations": [],
        "structures": [],
        "artifacts": [],
    }
    phase_diagram_rows: list[dict[str, Any]] = []
    topology_comparison_rows: list[dict[str, Any]] = []
    for result in results:
        scientific_rows = _paper_scientific_rows(result)
        for kind, kind_rows in scientific_rows.items():
            scientific_exports[kind].extend(kind_rows)
        phase_diagram_rows.extend(_phase_diagram_export_rows(result))
        topology_comparison_rows.extend(_topology_soc_comparison_rows(result))
        aggregate = result["aggregate"]
        landscape = result["material_landscape"]
        shared_summary = result["shared_discovery_ledger"]
        target_audit = result["protocol_conformance"]["stage_2_target_audit"]
        row = {
            "case_name": result["case_name"],
            "qualified_route_count": aggregate["qualified_route_count"],
            "attempted_route_count": aggregate["attempted_route_count"],
            "aggregate_bundle_id": aggregate["bundle_id"],
            "aggregate_source_record_count": aggregate["source_record_count"],
            "aggregate_distinct_sources_json": canonical_json(
                aggregate["source_record_sources"]
            ),
            "aggregate_distinct_source_count": aggregate["source_record_source_count"],
            "aggregate_distinct_providers_json": canonical_json(
                aggregate["source_record_providers"]
            ),
            "aggregate_distinct_provider_count": aggregate[
                "source_record_provider_count"
            ],
            "aggregate_execution_status_counts_json": canonical_json(
                aggregate["execution_status_counts"]
            ),
            "aggregate_record_result_counts_json": canonical_json(
                aggregate["record_result_counts"]
            ),
            "aggregate_completeness_counts_json": canonical_json(
                aggregate["record_completeness_counts"]
            ),
            "aggregate_capacity_limitation_count": len(
                aggregate["capacity_limitations"]
            ),
            "rq1_rq2_shared_bundle_id": shared_summary["authoritative_bundle_id"],
            "aggregate_source_records_call_count": shared_summary[
                "aggregate_source_records_call_count"
            ],
            "additional_source_record_acquisition_count": shared_summary[
                "additional_source_record_acquisition_count"
            ],
            "shared_discovery_gap_count": shared_summary["gap_count"],
            "shared_discovery_gaps_json": canonical_json(shared_summary["gaps"]),
            "shared_discovery_complete_inventory_eligible": shared_summary[
                "complete_inventory_eligible"
            ],
            "material_landscape_data_categories_json": canonical_json(
                landscape["data_categories_actually_present"]
            ),
            "material_landscape_contributing_sources_json": canonical_json(
                [row["source"] for row in landscape["contributing_exact_sources"]]
            ),
            "cross_source_union_adds_json": canonical_json(
                landscape["what_cross_source_union_adds"]
            ),
            "rq3_method_applicability": result["rq3_method_applicability"]["status"],
            "rq3_method_applicability_reason": result["rq3_method_applicability"][
                "reason"
            ],
            "rq3_expected_method_names_json": canonical_json(
                result["rq3_method_applicability"]["expected_method_names"]
            ),
            "qualified_source_route_count_semantics": QUALIFIED_ROUTE_COUNT_SEMANTICS,
            "thermochemical_entry_count": sum(
                _thermochemical_entry_count(item)
                for item in _case_items(result, "scientific_artifact")
                if item["artifact_type"] == "thermochemical_entry_set"
            ),
            "explicit_method_names_json": canonical_json(
                [method["method_name"] for method in result["explicit_methods"]]
            ),
            "preregistered_exact_target_count": target_audit[
                "preregistered_target_count"
            ],
            "found_exact_target_count": target_audit["found_target_count"],
            "missing_exact_target_count": target_audit["missing_target_count"],
            "executed_exact_enrichment_count": target_audit[
                "executed_enrichment_route_count"
            ],
            "succeeded_exact_enrichment_count": target_audit[
                "succeeded_enrichment_route_count"
            ],
            "failed_or_unavailable_exact_enrichment_count": target_audit[
                "failed_or_unavailable_enrichment_route_count"
            ],
            "researcher_use": landscape["researcher_use"],
            "actionable_next_step": landscape["actionable_next_step"],
            "external_handoff": landscape["external_handoff"],
            "unresolved_gaps_json": canonical_json(landscape["unresolved_gaps"]),
            "prohibited_claims": landscape["prohibited_claims"],
        }
        rows.append(row)
        figure_cases.append(
            {
                "case_name": result["case_name"],
                "scientific_task": landscape["scientific_task"],
                "aggregate": {
                    "qualified_route_count": aggregate["qualified_route_count"],
                    "ready_route_count": aggregate["ready_route_count"],
                    "attempted_route_count": aggregate["attempted_route_count"],
                    "execution_status_counts": aggregate["execution_status_counts"],
                    "record_result_counts": aggregate["record_result_counts"],
                    "record_completeness_counts": aggregate[
                        "record_completeness_counts"
                    ],
                    "capacity_limitation_count": len(aggregate["capacity_limitations"]),
                    "source_record_count": aggregate["source_record_count"],
                    "distinct_source_count": aggregate["source_record_source_count"],
                    "distinct_provider_count": aggregate[
                        "source_record_provider_count"
                    ],
                },
                "shared_discovery_ledger": shared_summary,
                "data_categories_actually_present": landscape[
                    "data_categories_actually_present"
                ],
                "cross_source_union_insights": [
                    {
                        "statement": claim["statement"],
                        "support_status": claim["support_status"],
                        "complete_inventory_support_status": claim[
                            "complete_inventory_support_status"
                        ],
                        "supporting_sources": [
                            support["source"]
                            for support in claim["supporting_contributions"]
                            if support["source"]
                            not in {
                                missing["source"]
                                for missing in claim["missing_supporting_contributions"]
                            }
                        ],
                        "missing_supporting_sources": [
                            missing["source"]
                            for missing in claim["missing_supporting_contributions"]
                        ],
                    }
                    for claim in landscape["what_cross_source_union_adds"]
                ],
                "exact_followup": {
                    "preregistered_target_count": target_audit[
                        "preregistered_target_count"
                    ],
                    "found_target_count": target_audit["found_target_count"],
                    "missing_target_count": target_audit["missing_target_count"],
                    "targets": [
                        {
                            "source": target["qualified_source_route"],
                            "source_id": target["source_id"],
                            "scientific_role": target["scientific_role"],
                            "status": target["status"],
                        }
                        for target in target_audit["targets"]
                    ],
                    "methods": [
                        {
                            "method_name": method["method_name"],
                            "succeeded": _method_result_succeeded(method),
                        }
                        for method in result["explicit_methods"]
                    ],
                    "case_result": _paper_highlights(result),
                },
                "researcher_use": landscape["researcher_use"],
                "actionable_next_step": landscape["actionable_next_step"],
                "external_handoff": landscape["external_handoff"],
                "unresolved_gaps": landscape["unresolved_gaps"],
                "prohibited_claim": landscape["prohibited_claims"],
            }
        )
        write_json(
            RESULTS / "case-traces" / f"{result['case_name']}.json",
            landscape,
        )
    with (RESULTS / "cases.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for name, export_rows in scientific_exports.items():
        path = RESULTS / f"{name}.csv"
        with path.open("w", newline="") as handle:
            if export_rows:
                writer = csv.DictWriter(handle, fieldnames=list(export_rows[0]))
                writer.writeheader()
                writer.writerows(export_rows)
    for path, export_rows in (
        (RESULTS / "phase-diagram-entries.csv", phase_diagram_rows),
        (RESULTS / "topology-soc-comparison.csv", topology_comparison_rows),
    ):
        with path.open("w", newline="") as handle:
            if export_rows:
                writer = csv.DictWriter(handle, fieldnames=list(export_rows[0]))
                writer.writeheader()
                writer.writerows(export_rows)
    write_json(
        RESULTS / "figure-ready.json",
        {
            "status": "release_bound_three_case_results",
            "stage_1_scope": STAGE_1_SCOPE,
            "qualified_source_route_count_semantics": QUALIFIED_ROUTE_COUNT_SEMANTICS,
            "case_count": 3,
            "cases": figure_cases,
        },
    )


def _paper_observation_identity_fields(
    row: dict[str, Any], *, csv_encoded: bool
) -> dict[str, Any]:
    return {
        "source": row["source"],
        "source_id": row["source_id"],
        "formula": row["formula"] or None if csv_encoded else row["formula"],
        "property": row["property"],
        "value": json.loads(row["value_json"]),
        "unit": row["unit"] or None if csv_encoded else row["unit"],
    }


def _validate_paper_observation_export_consistency(
    results_by_case: dict[str, dict[str, Any]],
) -> None:
    with (RESULTS / "observations.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    for case_name in CASES:
        expected = [
            _paper_observation_identity_fields(row, csv_encoded=False)
            for row in _paper_scientific_rows(results_by_case[case_name])[
                "observations"
            ]
        ]
        csv_observations = [
            _paper_observation_identity_fields(row, csv_encoded=True)
            for row in csv_rows
            if row["case_name"] == case_name
        ]
        if csv_observations != expected:
            raise ValueError(f"{case_name}: observations.csv export drift")


def _diagnose_stage1_product_blockers(
    case_name: str, outcomes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Classify only source-independent contract/request failures as product blockers."""
    blockers: list[dict[str, Any]] = []
    for outcome in outcomes:
        reason_code = outcome.get("reason_code")
        message = outcome.get("message")
        http_match = re.search(
            r"\bHTTP\s+(400|404|405|422)\b", message or "", re.IGNORECASE
        )
        if reason_code == "adapter_exception":
            category = "adapter_exception"
            http_status = None
        elif http_match is not None:
            category = "non_authorization_http_4xx_requires_product_investigation"
            http_status = int(http_match.group(1))
        else:
            continue
        core = {
            "case_name": case_name,
            "source": outcome.get("qualified_source") or outcome.get("source"),
            "operation": outcome.get("operation"),
            "reason_code": reason_code,
            "diagnostic_category": category,
            "http_status": http_status,
        }
        blockers.append(
            {
                "blocker_id": f"stage1-{sha256_bytes(canonical_bytes(core))[:16]}",
                **core,
                "severity": "P0_for_protocol_eligibility",
                "scientific_consequence": "A ready Stage-1 source route did not complete because of an unresolved adapter or request-contract failure; the case is protocol-ineligible until the product behavior is resolved.",
                "classification_scope": "Source-independent diagnostic rule. Entitlement/configuration HTTP 401/402/403, HTTP 429, timeouts, HTTP 5xx, and ordinary upstream warnings are preserved but are not automatically classified as product bugs.",
            }
        )
    return sorted(
        {row["blocker_id"]: row for row in blockers}.values(),
        key=lambda row: row["blocker_id"],
    )


def _diagnose_case_product_blockers(result: dict[str, Any]) -> list[dict[str, Any]]:
    executions = [
        execution
        for capsule in result["evidence_bundles"]
        if capsule["bundle_role"] == "primary_aggregate"
        for execution in _bundle_execution_rows(capsule["evidence_bundle"])
        if execution["operation"] == "search_materials"
    ]
    return _diagnose_stage1_product_blockers(result["case_name"], executions)


def write_product_blockers(results: list[dict[str, Any]]) -> None:
    identity = load_json(IDENTITY_PATH)
    lifepo4 = next(
        result for result in results if result["case_name"] == "lifepo4-stability"
    )
    blockers = [
        blocker
        for result in results
        for blocker in result.get("unresolved_product_blockers", [])
    ]
    if not _phase_diagram_method_is_safe(lifepo4):
        outcomes = _thermochemical_outcomes(lifepo4)
        entry_sets = _complete_thermochemical_entry_sets(lifepo4)
        reproduction_path: Path | None = None
        failed_outcomes = [
            outcome for outcome in outcomes if outcome["execution_status"] == "failed"
        ]
        raw_path = RAW / identity["package_version"] / "lifepo4-stability.json"
        if failed_outcomes and raw_path.is_file():
            raw = load_json(raw_path)
            failed_acquisitions = [
                acquisition
                for run in raw["runs"]
                for acquisition in run["acquisitions"]
                if acquisition["route"]["operation"] == "get_thermochemical_entries"
                and acquisition["outcome"]["execution_status"] == "failed"
            ]
            if len(failed_acquisitions) == 1:
                acquisition = failed_acquisitions[0]
                reproduction_path = (
                    RESULTS
                    / "diagnostics"
                    / "thermochemical-entry-set-typed-reproduction.json"
                )
                write_json(
                    reproduction_path,
                    {
                        "schema_version": "matrouter.paper-typed-reproduction/2",
                        "release_binding": {
                            "package": f"matrouter=={identity['package_version']}",
                            "tag": identity["release_tag"],
                            "commit": identity["product_commit"],
                        },
                        "reproduction_kind": "stored_exact_typed_acquisition_slice",
                        "raw_capture": str(raw_path.relative_to(ROOT)),
                        "requirement": acquisition["requirement"],
                        "route": acquisition["route"],
                        "outcome": acquisition["outcome"],
                        "second_network_request_issued": False,
                        "limitations": [
                            "This is the exact public-contract slice from the one preregistered full run, not a selective retry.",
                            "The public failed outcome returned no entry members, so the upstream entry count and smallest failing set cannot be established offline.",
                        ],
                    },
                )
        blockers.append(
            {
                "blocker_id": (
                    f"matrouter-{identity['package_version']}-"
                    "lifepo4-exact-phase-diagram-gate"
                ),
                "severity": "P0_for_lifepo4_explicit_phase_diagram",
                "release": f"matrouter=={identity['package_version']}",
                "product_commit": identity["product_commit"],
                "public_operation": "get_thermochemical_entries",
                "exact_filter": {"thermo_types": [THERMO_TYPE]},
                "chemical_system": ["Fe", "Li", "O", "P"],
                "engineering_ceiling_authority": "matrouter_product_defaults",
                "typed_outcomes": outcomes,
                "complete_entry_set_count": len(entry_sets),
                "complete_entry_counts": [item["entry_count"] for item in entry_sets],
                "minimal_typed_reproduction": (
                    str(reproduction_path.relative_to(ROOT))
                    if reproduction_path is not None
                    else None
                ),
                "scientific_consequence": "The exact complete same-Bundle entry-set and successful bound phase-diagram gates were not all satisfied, so LiFePO4 is ineligible for a hull statement.",
                "workaround_policy": "No evaluation-side reconstruction, truncation, cross-source mixing, or lowered completeness gate is permitted.",
                "release_tag": identity["release_tag"],
            }
        )
    write_json(
        RESULTS / "product-blockers.json",
        {
            "schema_version": "matrouter.paper-product-blockers/2",
            "blocker_count": len(blockers),
            "blockers": blockers,
        },
    )


def _bi2se3_topology_pair_present(result: dict[str, Any]) -> bool:
    by_source_id: dict[str, set[str]] = {}
    for item in _case_items(result, "scientific_artifact"):
        if item["artifact_type"] not in {
            "topology_no_soc",
            "topology_soc",
        }:
            continue
        if item["identity"]["source"] != "materialsgalaxy:topo_crystals":
            return False
        descriptor = _artifact_content(item)
        expected_soc = item["artifact_type"] == "topology_soc"
        if descriptor.get("soc") is not expected_soc:
            return False
        by_source_id.setdefault(item["identity"]["source_id"], set()).add(
            item["artifact_type"]
        )
    return by_source_id == {
        "mg-35598": {"topology_no_soc", "topology_soc"},
        "mg-2145449": {"topology_no_soc", "topology_soc"},
    }


def _method_result_succeeded(method: dict[str, Any]) -> bool:
    exact_inputs = method.get("exact_input_item_ids")
    method_result = method.get("result")
    return (
        isinstance(exact_inputs, list)
        and bool(exact_inputs)
        and isinstance(method_result, dict)
        and isinstance(method_result.get("result_id"), str)
    )


def _method_inputs_bind_declared_bundles(
    result: dict[str, Any], method: dict[str, Any]
) -> bool:
    exact_inputs = method.get("exact_input_item_ids")
    if not isinstance(exact_inputs, list) or not exact_inputs:
        return False
    items_by_bundle = {
        bundle["bundle_id"]: {item["item_id"] for item in bundle["evidence_items"]}
        for bundle in _case_bundles(result)
    }
    declared_bundle_ids = method.get("input_bundle_ids")
    if declared_bundle_ids is None:
        declared_bundle_ids = [method.get("input_bundle_id")]
    if (
        not isinstance(declared_bundle_ids, list)
        or not declared_bundle_ids
        or any(bundle_id not in items_by_bundle for bundle_id in declared_bundle_ids)
    ):
        return False
    return all(
        any(item_id in items_by_bundle[bundle_id] for bundle_id in declared_bundle_ids)
        for item_id in exact_inputs
    )


def _complete_spectral_artifact_ids(result: dict[str, Any]) -> set[str]:
    return {
        item["item_id"]
        for item in _case_items(result, "scientific_artifact")
        if item["artifact_type"] in {"band_structure", "density_of_states"}
        and item.get("content")
        and item.get("identity", {}).get("source")
        and item.get("identity", {}).get("source_id")
    }


def _successful_spectral_render_input_ids(result: dict[str, Any]) -> set[str]:
    complete_artifacts = _complete_spectral_artifact_ids(result)
    items_by_bundle = {
        bundle["bundle_id"]: {item["item_id"] for item in bundle["evidence_items"]}
        for bundle in _case_bundles(result)
    }
    successful: set[str] = set()
    for method in result["explicit_methods"]:
        if method.get("method_name") not in {
            "render_band_structure",
            "render_density_of_states",
        } or not _method_result_succeeded(method):
            continue
        exact_inputs = method["exact_input_item_ids"]
        if len(exact_inputs) != 1 or exact_inputs[0] not in complete_artifacts:
            continue
        if exact_inputs[0] not in items_by_bundle.get(
            method.get("input_bundle_id"), set()
        ):
            continue
        method_result = method["result"]
        plot = method_result.get("plot_artifact") or {}
        if (
            method_result.get("input", {}).get("artifact_item_id") == exact_inputs[0]
            and plot.get("input_artifact_item_id") == exact_inputs[0]
            and plot.get("content_sha256")
        ):
            successful.add(exact_inputs[0])
    return successful


def _mos2_preregistered_methods_are_safe(result: dict[str, Any]) -> bool:
    target_artifacts = [
        item
        for item in _case_items(result, "scientific_artifact")
        if item.get("identity", {}).get("source") == "materials_project"
        and item.get("identity", {}).get("source_id") == "mp-2815"
        and item.get("artifact_type") in {"band_structure", "density_of_states"}
        and item.get("content")
    ]
    if len(target_artifacts) != 2 or {
        item["artifact_type"] for item in target_artifacts
    } != {"band_structure", "density_of_states"}:
        return False
    target_ids = {item["item_id"] for item in target_artifacts}
    render_methods = [
        method
        for method in result["explicit_methods"]
        if method.get("method_name")
        in {"render_band_structure", "render_density_of_states"}
        and _method_result_succeeded(method)
    ]
    if len(render_methods) != 2 or {
        method["method_name"] for method in render_methods
    } != {"render_band_structure", "render_density_of_states"}:
        return False
    if {method["exact_input_item_ids"][0] for method in render_methods} != target_ids:
        return False
    match_methods = [
        method
        for method in result["explicit_methods"]
        if method.get("method_name") == "match_structures"
        and _method_result_succeeded(method)
    ]
    if len(match_methods) != 1:
        return False
    match = match_methods[0]
    structure_items = {
        item["item_id"]: (bundle["bundle_id"], item)
        for bundle in _target_bundles(result)
        for item in _bundle_items(bundle, "structure")
        if (
            item.get("identity", {}).get("source"),
            item.get("identity", {}).get("source_id"),
        )
        in {
            (
                "aflow",
                "aflowlib.duke.edu:AFLOWDATA/ICSD_WEB/HEX/Mo1S2_ICSD_644246",
            ),
            ("materials_project", "mp-2815"),
        }
    }
    exact_ids = match.get("exact_input_item_ids")
    if not isinstance(exact_ids, list) or len(exact_ids) != 2:
        return False
    if set(exact_ids) != set(structure_items) or match.get("input_bundle_ids") != [
        structure_items[item_id][0] for item_id in exact_ids
    ]:
        return False
    request_items = [
        match.get("request", {}).get(name, {}).get("item")
        for name in ("first", "second")
    ]
    return request_items == [structure_items[item_id][1] for item_id in exact_ids]


def _thermochemical_outcomes(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        execution
        for bundle in _case_bundles(result)
        for execution in _bundle_execution_rows(bundle)
        if execution["operation"] == "get_thermochemical_entries"
    ]


def _complete_thermochemical_entry_sets(
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    complete_outcomes = [
        outcome
        for outcome in _thermochemical_outcomes(result)
        if outcome["execution_status"] == "succeeded"
        and (outcome.get("record_completeness") or {}).get("state") == "complete"
    ]
    entry_sets = [
        item
        for item in _case_items(result, "scientific_artifact")
        if item.get("artifact_type") == "thermochemical_entry_set"
        and item.get("content")
        and _thermochemical_entry_count(item) >= 2
        and item.get("identity", {}).get("source") == "materials_project"
    ]
    return entry_sets if len(complete_outcomes) == 1 else []


def _phase_diagram_method_is_safe(result: dict[str, Any]) -> bool:
    entry_sets = _complete_thermochemical_entry_sets(result)
    if len(entry_sets) != 1:
        return False
    entry_set = entry_sets[0]
    methods = [
        method
        for method in result["explicit_methods"]
        if method.get("method_name") == "compute_phase_diagrams"
        and _method_result_succeeded(method)
    ]
    if len(methods) != 1:
        return False
    method = methods[0]
    request_datasets = method.get("request", {}).get("datasets", [])
    result_datasets = method.get("result", {}).get("datasets", [])
    if len(request_datasets) != 1 or len(result_datasets) != 1:
        return False
    request_entry_set = request_datasets[0].get("entry_set")
    input_manifest = result_datasets[0].get("input_manifest") or {}
    manifest_entry_set = input_manifest.get("entry_set")
    entries = result_datasets[0].get("entries")
    input_bundle_ids = [
        capsule["evidence_bundle"]["bundle_id"]
        for capsule in result["evidence_bundles"]
        if any(
            item["item_id"] == entry_set["item_id"]
            for item in capsule["evidence_bundle"]["evidence_items"]
        )
    ]
    return (
        len(input_bundle_ids) == 1
        and method.get("input_bundle_id") == input_bundle_ids[0]
        and method["exact_input_item_ids"] == [entry_set["item_id"]]
        and request_entry_set == entry_set
        and manifest_entry_set == entry_set
        and input_manifest.get("manifest_id")
        and isinstance(entries, list)
        and len(entries) == _thermochemical_entry_count(entry_set)
        and all(
            row.get("reference", {}).get("entry_set_item_id") == entry_set["item_id"]
            for row in entries
        )
    )


def _case_paper_eligible(result: dict[str, Any]) -> bool:
    if result.get("unresolved_product_blockers"):
        return False
    if not result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]:
        return False
    if not result.get("aggregate"):
        return False
    if not result.get("material_landscape", {}).get(
        "all_declared_claims_supported", False
    ):
        return False
    if result.get("material_landscape") != _material_landscape_trace(
        result, result["task_spec"]
    ):
        return False
    case_name = result["case_name"]
    if case_name == "mos2-band-gap":
        return _mos2_preregistered_methods_are_safe(result)
    if case_name == "lifepo4-stability":
        return _phase_diagram_method_is_safe(result)
    if case_name == "bi2se3-topology":
        return _bi2se3_topology_pair_present(result)
    raise ValueError(f"unknown case: {case_name}")


def _paper_result_status(result: dict[str, Any]) -> str:
    return (
        "protocol_eligible"
        if result["paper_results_eligible"]
        else "protocol_ineligible"
    )


def write_internal_protocol_review(
    results: list[dict[str, Any]], raw_paths: dict[str, Path] | None = None
) -> None:
    mos2 = next(result for result in results if result["case_name"] == "mos2-band-gap")
    mos2_highlights = _paper_highlights(mos2)
    bi2se3 = next(
        result for result in results if result["case_name"] == "bi2se3-topology"
    )
    blocker_report = load_json(RESULTS / "product-blockers.json")
    external_blockers = [
        {
            "severity": "P0",
            "finding": f"Unresolved product blocker: {blocker['blocker_id']}",
            "evidence": "results/product-blockers.json",
            "consequence": blocker["scientific_consequence"],
        }
        for blocker in blocker_report["blockers"]
    ]
    applicable_results = [
        result
        for result in results
        if result["rq3_method_applicability"]["status"] == "applicable"
    ]
    expected_methods_by_case = {
        result["case_name"]: [
            method
            for method in result["explicit_methods"]
            if method.get("method_name")
            in result["rq3_method_applicability"]["expected_method_names"]
            and _method_result_succeeded(method)
        ]
        for result in applicable_results
    }
    applicable_cases_have_expected_methods = all(
        {
            method["method_name"]
            for method in expected_methods_by_case[result["case_name"]]
        }
        == set(result["rq3_method_applicability"]["expected_method_names"])
        for result in applicable_results
    )
    applicable_methods_bind_declared_exact_bundle_inputs = all(
        bool(expected_methods_by_case[result["case_name"]])
        and all(
            _method_inputs_bind_declared_bundles(result, method)
            for method in expected_methods_by_case[result["case_name"]]
        )
        and (
            result["case_name"] != "lifepo4-stability"
            or _phase_diagram_method_is_safe(result)
        )
        for result in applicable_results
    )
    lifepo4 = next(
        result for result in results if result["case_name"] == "lifepo4-stability"
    )
    thermo_outcomes = _thermochemical_outcomes(lifepo4)
    phase_methods = [
        method
        for method in lifepo4["explicit_methods"]
        if method.get("method_name") == "compute_phase_diagrams"
    ]
    failed_or_incomplete_entry_sets_never_enter_hull = bool(thermo_outcomes) and (
        _phase_diagram_method_is_safe(lifepo4)
        if phase_methods
        else all(
            outcome["execution_status"] != "succeeded"
            or (outcome.get("record_completeness") or {}).get("state") != "complete"
            for outcome in thermo_outcomes
        )
    )
    open_findings: list[dict[str, Any]] = []
    for result in results:
        landscape = result["material_landscape"]
        if not landscape["all_declared_claims_supported"]:
            open_findings.append(
                {
                    "severity": "P1",
                    "case_name": result["case_name"],
                    "finding": "One or more preregistered cross-source landscape claims were not supported by records returned in this frozen run.",
                    "current_status": "protocol_ineligible",
                    "evidence": f"results/case-traces/{result['case_name']}.json",
                    "required_resolution": "Preserve the missing source/category contributions as explicit gaps; do not fabricate, substitute, or selectively rerun them.",
                }
            )
    for applicable in applicable_results:
        expected_names = set(
            applicable["rq3_method_applicability"]["expected_method_names"]
        )
        successful_names = {
            method["method_name"]
            for method in expected_methods_by_case[applicable["case_name"]]
        }
        if successful_names != expected_names:
            open_findings.append(
                {
                    "severity": "P0",
                    "case_name": applicable["case_name"],
                    "finding": "RQ3 is applicable but one or more preregistered explicit methods are absent or unsuccessful.",
                    "current_status": "protocol_ineligible",
                    "evidence": "results/product-blockers.json",
                    "required_resolution": "Inspect stored target, route, outcome, and exact-input evidence without dynamic substitution or lowered gates.",
                }
            )
    review = {
        "schema_version": "matrouter.paper-internal-protocol-review/8",
        "review_name": "internal_protocol_review",
        "review_kind": "deterministic_internal_protocol_and_scientific_boundary_checklist",
        "independence_claim": False,
        "external_ai_expert_or_peer_review_claim": False,
        "review_scope": "Deterministic internal checklist over the frozen protocol, stored artifacts, exact method bindings, reproducibility, and declared scientific boundaries; not an independent AI review, expert adjudication, or external peer review.",
        "paper_results_eligibility_semantics": PAPER_ELIGIBILITY_SEMANTICS,
        "checks": {
            "three_named_cases_only": [result["case_name"] for result in results]
            == list(CASES),
            "three_common_research_questions": all(
                result["research_questions"] == COMMON_RESEARCH_QUESTIONS
                and result["task_spec"]["research_question_ids"]
                == list(COMMON_RESEARCH_QUESTIONS)
                for result in results
            ),
            "one_primary_aggregate_attempts_all_qualified_routes_with_typed_capacity_stops": all(
                result["case_interpretation"]["stage_1_scope"] == STAGE_1_SCOPE
                for result in results
            ),
            "rq1_and_rq2_share_one_authoritative_discovery_ledger": all(
                result["case_interpretation"]["shared_discovery_scope"]
                == SHARED_DISCOVERY_SCOPE
                and result["protocol_conformance"]["shared_discovery_ledger"]["passed"]
                and result["shared_discovery_ledger"]["rq1_rq2_same_bundle"]
                and result["shared_discovery_ledger"][
                    "aggregate_source_records_call_count"
                ]
                == 1
                and result["shared_discovery_ledger"][
                    "additional_source_record_acquisition_count"
                ]
                == 0
                for result in results
            ),
            "incomplete_shared_discovery_never_claims_complete_inventory": all(
                result["shared_discovery_ledger"]["complete_inventory_eligible"]
                == (result["shared_discovery_ledger"]["gap_count"] == 0)
                for result in results
            ),
            "paper_results_eligible_is_protocol_only": all(
                result["paper_results_eligibility_semantics"]
                == PAPER_ELIGIBILITY_SEMANTICS
                for result in results
            ),
            "stage_2_uses_only_preregistered_exact_targets": all(
                result["actual_retrieval_strategy"]["stage_2_targets"]
                == result["task_spec"]["stage_2_targets"]
                for result in results
            ),
            "preregistered_exact_target_followups_succeed": all(
                result["protocol_conformance"]["stage_2_target_audit"]["passed"]
                for result in results
            ),
            "primary_aggregate_has_real_cross_source_records_each_case": all(
                result.get("aggregate", {}).get("real_cross_source_records")
                and result["protocol_conformance"]["single_primary_all_route_aggregate"]
                and any(
                    capsule["bundle_role"] == "primary_aggregate"
                    and capsule["evidence_bundle"]["bundle_id"]
                    == result["aggregate"]["bundle_id"]
                    for capsule in result["evidence_bundles"]
                )
                for result in results
            ),
            "rq2_material_landscape_trace_is_source_supported": all(
                result.get("material_landscape")
                == _material_landscape_trace(result, result["task_spec"])
                and result["material_landscape"]["primary_aggregate_bundle_id"]
                == result["primary_result_bundle_id"]
                and result["material_landscape"]["all_declared_claims_supported"]
                for result in results
            ),
            "only_declared_single_ledger_run_roles": all(
                all(
                    run["run_role"]
                    in {
                        "primary_aggregate",
                        "target_followup",
                        "thermochemical",
                    }
                    for run in load_json(
                        (
                            raw_paths
                            or {
                                case: RAW
                                / FINAL_RELEASE_BINDING["package_version"]
                                / f"{case}.json"
                                for case in CASES
                            }
                        )[result["case_name"]]
                    )["runs"]
                )
                for result in results
            ),
            "all_qualified_source_routes_executed_each_case": all(
                len(result["coverage_matrix"])
                == len(result["actual_retrieval_strategy"]["qualified_source_routes"])
                and all(
                    row["qualified"] and row["executed"]
                    for row in result["coverage_matrix"]
                )
                for result in results
            ),
            "failed_never_verified_empty": all(
                not row["verified_empty"]
                for result in results
                for row in result["coverage_matrix"]
                if row["failed"]
            ),
            "formula_phase_and_cross_frame_guardrails_present": all(
                result["task_spec"]["prohibited_statement"] for result in results
            ),
            "lifepo4_formation_energy_not_hull_and_frames_not_mixed": (
                "Formation energy is distinct"
                in next(
                    result
                    for result in results
                    if result["case_name"] == "lifepo4-stability"
                )["task_spec"]["context_differences"][0]
                and "mix sources or energy frames"
                in next(
                    result
                    for result in results
                    if result["case_name"] == "lifepo4-stability"
                )["task_spec"]["prohibited_statement"]
            ),
            "mos2_has_no_unified_gap_claim": "universal MoS2 band gap"
            in next(
                result for result in results if result["case_name"] == "mos2-band-gap"
            )["task_spec"]["prohibited_statement"],
            "bi2se3_remains_source_native_not_validated": "independently validated topology"
            in bi2se3["task_spec"]["prohibited_statement"],
            "bi2se3_exact_source_native_soc_pair_present": _bi2se3_topology_pair_present(
                bi2se3
            ),
            "mos2_catalog_not_phase_resolved_and_no_experimental_gap_claim": (
                mos2_highlights["result_scope"]
                == "capacity_bounded_multi_source_structure_and_electronic_landscape_not_phase_resolved_gap_answer"
                and mos2_highlights[
                    "explicitly_identified_experimental_band_gap_observation_count"
                ]
                == 0
            ),
            "lifepo4_frame_and_tolerance_semantics_declared": (
                "compatibility-mixed frame"
                in lifepo4["task_spec"]["context_differences"][1]
                and "not DFT uncertainty"
                in lifepo4["task_spec"]["context_differences"][2]
                and bool(_phase_diagram_export_rows(lifepo4))
                and all(
                    "energy_above_hull_eV_per_atom" in row
                    for row in _phase_diagram_export_rows(lifepo4)
                )
            ),
            "bi2se3_two_phase_by_soc_descriptive_table": (
                len(_topology_soc_comparison_rows(bi2se3)) == 4
                and {
                    (
                        row["source_id"],
                        row["source_native_space_group_symbol"],
                        row["soc"],
                        row["materials_galaxy_reported_topology_class"],
                    )
                    for row in _topology_soc_comparison_rows(bi2se3)
                }
                == {
                    ("mg-35598", "R-3m", False, "Triv_Ins"),
                    ("mg-35598", "R-3m", True, "TI"),
                    ("mg-2145449", "Pnma", False, "Triv_Ins"),
                    ("mg-2145449", "Pnma", True, "Triv_Ins"),
                }
            ),
            "raw_replay_matches_stored_bundle": all(
                canonical_bytes(
                    replay_case(
                        result["case_name"],
                        None if raw_paths is None else raw_paths[result["case_name"]],
                    )
                )
                == canonical_bytes(result["evidence_bundles"])
                for result in results
            ),
            "applicable_cases_have_expected_methods": applicable_cases_have_expected_methods,
            "applicable_methods_bind_declared_exact_bundle_inputs": applicable_methods_bind_declared_exact_bundle_inputs,
            "not_applicable_cases_do_not_claim_explicit_methods": all(
                not result["explicit_methods"]
                for result in results
                if result["rq3_method_applicability"]["status"] == "not_applicable"
            ),
            "failed_or_incomplete_entry_sets_never_enter_hull": failed_or_incomplete_entry_sets_never_enter_hull,
            "lifepo4_complete_exact_entry_set_and_result_manifest_binding": _phase_diagram_method_is_safe(
                lifepo4
            ),
            "capture_eligibility_matches_stage2_conformance": all(
                result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
                == (
                    result["protocol_conformance"]["single_primary_all_route_aggregate"]
                    and result["protocol_conformance"]["shared_discovery_ledger"][
                        "passed"
                    ]
                    and result["protocol_conformance"]["stage_2_target_audit"]["passed"]
                )
                for result in results
            ),
            "unresolved_product_blockers_make_cases_ineligible": all(
                not result.get("unresolved_product_blockers")
                or not result["paper_results_eligible"]
                for result in results
            ),
            "nonconformant_case_results_are_not_paper_eligible": all(
                result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
                or not result["paper_results_eligible"]
                for result in results
            ),
            "paper_scientific_exports_present": all(
                (RESULTS / name).is_file()
                for name in (
                    "observations.csv",
                    "structures.csv",
                    "artifacts.csv",
                    "rq1-rq2-shared-ledger-audit.json",
                    "phase-diagram-entries.csv",
                    "topology-soc-comparison.csv",
                )
            )
            and all(
                (RESULTS / "case-traces" / f"{case}.json").is_file() for case in CASES
            ),
        },
        "open_p0_p1_protocol_findings": open_findings,
        "external_execution_blockers": external_blockers,
        "conclusion": (
            "All three cases satisfy the frozen protocol-eligibility gates, including declared exact-Bundle method-input binding where applicable. This internal checklist does not validate scientific truth and is not external peer review."
            if not open_findings and not external_blockers
            else "One or more preregistered eligibility gates remain unsatisfied; the stored typed outcomes and exact input bindings determine the limitation without a workaround."
        ),
    }
    write_json(RESULTS / "internal-protocol-review.json", review)


def _paper_export_paths() -> tuple[Path, ...]:
    return (
        RESULTS / "cases.csv",
        RESULTS / "coverage.csv",
        RESULTS / "source-outcome-audit.csv",
        RESULTS / "source-completeness-review.json",
        RESULTS / "rq1-rq2-shared-ledger-audit.json",
        RESULTS / "observations.csv",
        RESULTS / "structures.csv",
        RESULTS / "artifacts.csv",
        RESULTS / "phase-diagram-entries.csv",
        RESULTS / "topology-soc-comparison.csv",
        RESULTS / "figure-ready.json",
        RESULTS / "product-blockers.json",
        RESULTS / "internal-protocol-review.json",
        *(
            path
            for path in sorted((RESULTS / "case-traces").glob("*.json"))
            if path.is_file()
        ),
        *(path for path in sorted(ARTIFACTS.glob("*")) if path.is_file()),
        *(
            path
            for path in sorted((RESULTS / "diagnostics").glob("*.json"))
            if path.is_file()
        ),
    )


def preflight() -> dict[str, Any]:
    from matrouter import create_router
    from matrouter.tools.evidence import (
        BeginEvidenceRunRequest,
        CapabilityRequest,
        EvidenceTools,
    )
    from matrouter.tools.run_state import SessionRunRegistry

    identity = verify_release_identity()
    router = create_router()
    try:
        tools = EvidenceTools(router, SessionRunRegistry())
        capability = tools.inspect_evidence_capabilities(CapabilityRequest())
        audit = _capability_audit(capability)
        aggregate_route_snapshots: dict[str, list[dict[str, Any]]] = {}
        for case_name in CASES:
            spec = case_spec(case_name)
            run = tools.begin_evidence_run(BeginEvidenceRunRequest())
            requirement = _create_requirement(
                tools,
                run.evidence_run_id,
                subject=_subject(formula=spec["formula"]),
                kind="source_record",
                constraints=_constraints(all_qualified=True),
            )
            routes = _route(tools, run.evidence_run_id, requirement)
            route_sources = [route.qualified_source for route in routes]
            if len(route_sources) != len(set(route_sources)):
                raise ValueError(
                    f"{case_name}: qualified source-route expansion mismatch"
                )
            materials_galaxy_routes = [
                route for route in routes if route.qualified_source == "materialsgalaxy"
            ]
            if (
                len(materials_galaxy_routes) != 1
                or not materials_galaxy_routes[0].aggregate_sources
                or any(
                    source.startswith("materialsgalaxy:") for source in route_sources
                )
            ):
                raise ValueError(
                    f"{case_name}: MaterialsGalaxy must be one provider-level aggregate execution route"
                )
            aggregate_route_snapshots[case_name] = [
                {
                    "qualified_source": route.qualified_source,
                    "aggregate_sources": list(route.aggregate_sources),
                    "state": "ready" if route.is_ready else "requires_configuration",
                }
                for route in routes
            ]
            catalog_bundle = _assemble_run(
                tools, run.evidence_run_id, [requirement], []
            )
            if len(catalog_bundle.routes) != len(route_sources):
                raise ValueError(
                    f"{case_name}: catalog Bundle qualified-route mismatch"
                )
        audit["aggregate_route_snapshots"] = aggregate_route_snapshots
        audit["qualified_aggregate_execution_route_count"] = len(
            aggregate_route_snapshots[CASES[0]]
        )
        return {"release_identity": identity, "capability_audit": audit}
    finally:
        router.close()


def _clear_active_results() -> None:
    if RESULTS.is_dir():
        shutil.rmtree(RESULTS)


def _assert_final_release_binding(identity: dict[str, Any]) -> None:
    mismatches = {
        field: identity.get(field)
        for field, expected in FINAL_RELEASE_BINDING.items()
        if identity.get(field) != expected
    }
    if mismatches:
        expected = ", ".join(
            f"{field}={value}" for field, value in FINAL_RELEASE_BINDING.items()
        )
        raise RuntimeError(f"v0.10.2 release-bound run is pending; expected {expected}")


def _planned_raw_paths(identity: dict[str, Any]) -> dict[str, Path]:
    return {
        case_name: RAW / identity["package_version"] / f"{case_name}.json"
        for case_name in CASES
    }


def _capture_protocol_document(
    *,
    identity: dict[str, Any],
    full_run_id: str,
    runtime_distribution: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "matrouter.paper-capture-protocol/1",
        "full_run_id": full_run_id,
        "protocol_version": PROTOCOL_VERSION,
        "release_binding": identity,
        "runtime_distribution": runtime_distribution,
        "execution_mode": "one_complete_nonselective_three_case_capture",
        "case_order": list(CASES),
        "research_questions": COMMON_RESEARCH_QUESTIONS,
        "stage_1_scope": STAGE_1_SCOPE,
        "shared_discovery_policy": SHARED_DISCOVERY_POLICY,
        "shared_discovery_scope": SHARED_DISCOVERY_SCOPE,
        "case_specs": [
            {
                "case_name": case_name,
                "path": f"cases/{case_name}.json",
                "sha256": file_sha256(ROOT / "cases" / f"{case_name}.json"),
                "spec": case_spec(case_name),
            }
            for case_name in CASES
        ],
        "runner_path": "experiment.py",
        "runner_sha256": file_sha256(Path(__file__)),
        "selective_rerun_permitted": False,
    }


def _write_capture_log(
    path: Path, full_run_id: str, events: list[dict[str, Any]]
) -> None:
    write_json(
        path,
        {
            "schema_version": "matrouter.paper-capture-log/1",
            "full_run_id": full_run_id,
            "events": events,
        },
    )


def _portable_abort_message(exc: BaseException) -> str:
    message = str(exc)
    for private_path in (str(Path.home()), str(ROOT), "/private/tmp"):
        message = message.replace(private_path, "<private-path>")
    message = re.sub(
        r"(?i)(api[_-]?key|token|secret)(\s*[=:]\s*)[^\s,;]+",
        r"\1\2<redacted>",
        message,
    )
    return message[:1000]


def run_all() -> None:
    if not FORMAL_CAPTURE_ENABLED:
        raise RuntimeError(FORMAL_CAPTURE_PAUSE_REASON)
    identity = verify_release_identity()
    _assert_final_release_binding(identity)
    final_raw_directory = RAW / identity["package_version"]
    planned_raw_paths = _planned_raw_paths(identity)
    if final_raw_directory.exists():
        raise FileExistsError(
            "planned final raw capture already exists; no active outputs were cleared: "
            + str(final_raw_directory)
        )
    preflight_result = preflight()
    if preflight_result["release_identity"] != identity:
        raise ValueError("preflight release identity drift")
    runtime_distribution = _runtime_distribution_audit()
    full_run_id = _new_full_run_id(identity["package_version"])
    capture_started_at = _utc_now()
    live_run_started = time.monotonic()
    staging_directory = RAW / ".staging" / full_run_id
    staging_directory.mkdir(parents=True, exist_ok=False)
    protocol_path = staging_directory / "protocol.json"
    log_path = staging_directory / "run-log.json"
    write_json(
        protocol_path,
        _capture_protocol_document(
            identity=identity,
            full_run_id=full_run_id,
            runtime_distribution=runtime_distribution,
        ),
    )
    events: list[dict[str, Any]] = [
        {
            "event": "full_capture_started",
            "at_utc": capture_started_at,
            "case_order": list(CASES),
            "release": f"matrouter=={identity['package_version']}",
        }
    ]
    _write_capture_log(log_path, full_run_id, events)
    _clear_active_results()
    results: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    raw_sha256_by_case: dict[str, str] = {}
    active_case: str | None = None
    try:
        for case_index, case_name in enumerate(CASES, start=1):
            active_case = case_name
            events.append(
                {
                    "event": "case_started",
                    "at_utc": _utc_now(),
                    "case_name": case_name,
                    "case_index": case_index,
                    "case_count": len(CASES),
                }
            )
            _write_capture_log(log_path, full_run_id, events)
            print(f"[{case_name}] starting", flush=True)
            staging_raw_path = staging_directory / f"{case_name}.json"
            _raw, result, case_coverage = acquire_case(
                case_name,
                full_run_id=full_run_id,
                raw_output_path=staging_raw_path,
            )
            result_path = CASE_RESULTS / f"{case_name}.json"
            write_json(result_path, result)
            results.append(result)
            coverage.extend(case_coverage)
            raw_sha256_by_case[case_name] = file_sha256(staging_raw_path)
            events.append(
                {
                    "event": "case_completed",
                    "at_utc": _utc_now(),
                    "case_name": case_name,
                    "case_elapsed_seconds": result["case_elapsed_seconds"],
                    "rq1_attempted_route_count": result["aggregate"][
                        "attempted_route_count"
                    ],
                    "shared_discovery_source_record_count": result[
                        "shared_discovery_ledger"
                    ]["source_record_count"],
                    "aggregate_source_records_call_count": result[
                        "shared_discovery_ledger"
                    ]["aggregate_source_records_call_count"],
                }
            )
            _write_capture_log(log_path, full_run_id, events)
            print(
                f"[{case_name}] captured in {result['case_elapsed_seconds']:.3f}s",
                flush=True,
            )
        active_case = None
        capture_completed_at = _utc_now()
        events.append(
            {
                "event": "full_capture_completed",
                "at_utc": capture_completed_at,
                "captured_cases": list(CASES),
                "selective_rerun": False,
            }
        )
        _write_capture_log(log_path, full_run_id, events)
        capture_files = [
            {
                "path": f"{case_name}.json",
                "sha256": raw_sha256_by_case[case_name],
                "role": "case_live_capture",
            }
            for case_name in CASES
        ]
        capture_files.extend(
            [
                {
                    "path": "protocol.json",
                    "sha256": file_sha256(protocol_path),
                    "role": "frozen_protocol_snapshot",
                },
                {
                    "path": "run-log.json",
                    "sha256": file_sha256(log_path),
                    "role": "structured_execution_log",
                },
            ]
        )
        write_json(
            staging_directory / "capture-manifest.json",
            {
                "schema_version": "matrouter.paper-capture-manifest/1",
                "status": "complete_immutable_three_case_capture",
                "full_run_id": full_run_id,
                "protocol_version": PROTOCOL_VERSION,
                "release_binding": identity,
                "runtime_distribution": runtime_distribution,
                "capture_started_at_utc": capture_started_at,
                "capture_completed_at_utc": capture_completed_at,
                "case_order": list(CASES),
                "all_cases_captured_once": True,
                "selective_rerun": False,
                "files": capture_files,
            },
        )
        staging_directory.rename(final_raw_directory)
    except BaseException as exc:
        events.append(
            {
                "event": "full_capture_abandoned",
                "at_utc": _utc_now(),
                "active_case": active_case,
                "exception_type": type(exc).__name__,
                "reason": _portable_abort_message(exc),
                "selective_retry_permitted": False,
                "restart_requirement": "A replacement attempt must rerun all three cases from the beginning.",
            }
        )
        _write_capture_log(log_path, full_run_id, events)
        write_json(
            staging_directory / "aborted-manifest.json",
            {
                "schema_version": "matrouter.paper-aborted-capture/1",
                "status": "abandoned_incomplete_full_capture",
                "full_run_id": full_run_id,
                "release": f"matrouter=={identity['package_version']}",
                "protocol_version": PROTOCOL_VERSION,
                "captured_case_prefix": [
                    case_name for case_name in CASES if case_name in raw_sha256_by_case
                ],
                "active_case": active_case,
                "exception_type": type(exc).__name__,
                "reason": _portable_abort_message(exc),
                "selective_retry_permitted": False,
            },
        )
        abandoned_directory = (
            RAW / "aborted" / identity["package_version"] / full_run_id
        )
        abandoned_directory.parent.mkdir(parents=True, exist_ok=True)
        staging_directory.rename(abandoned_directory)
        raise

    raw_paths = planned_raw_paths
    entries: list[dict[str, Any]] = []
    for result in results:
        case_name = result["case_name"]
        raw_path = raw_paths[case_name]
        result_path = CASE_RESULTS / f"{case_name}.json"
        entries.append(
            {
                "case_name": case_name,
                "raw_path": str(raw_path.relative_to(ROOT)),
                "raw_sha256": file_sha256(raw_path),
                "result_path": str(result_path.relative_to(ROOT)),
                "result_sha256": file_sha256(result_path),
                "bundle_ids": [bundle["bundle_id"] for bundle in _case_bundles(result)],
                "shared_discovery_ledger": result["shared_discovery_ledger"],
                "case_spec_sha256": file_sha256(ROOT / "cases" / f"{case_name}.json"),
                "paper_result_status": result["paper_result_status"],
            }
        )
    export_results(results, coverage)
    write_product_blockers(results)
    write_internal_protocol_review(results, raw_paths)
    paper_results_eligible = all(
        result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
        for result in results
    ) and all(result["paper_results_eligible"] for result in results)
    manifest = {
        "schema_version": "matrouter.paper-manifest/16",
        "full_run_id": full_run_id,
        "experiment_id": experiment_id(identity),
        "status": (
            "three_case_frozen_protocol_complete"
            if paper_results_eligible
            else "three_case_frozen_protocol_run_ineligible"
        ),
        "case_count": 3,
        "paper_results_eligible": paper_results_eligible,
        "paper_results_eligibility_semantics": PAPER_ELIGIBILITY_SEMANTICS,
        "ineligibility_reasons": (
            []
            if paper_results_eligible
            else [
                f"{result['case_name']} did not meet its preregistered case-level eligibility condition or has an unresolved product blocker."
                for result in results
                if not result["paper_results_eligible"]
            ]
        ),
        "protocol_version": PROTOCOL_VERSION,
        "research_questions": COMMON_RESEARCH_QUESTIONS,
        "shared_discovery_policy": SHARED_DISCOVERY_POLICY,
        "rq3_method_applicability": {
            result["case_name"]: result["rq3_method_applicability"]
            for result in results
        },
        "core_boundary": "MatRouter routes source-qualified evidence and exact method inputs; the Agent builds the case-specific material landscape and scientific handoff.",
        "reference_assessments_enabled": False,
        "release_identity": identity,
        "runtime_distribution": runtime_distribution,
        "raw_capture_manifest": {
            "path": str(
                (final_raw_directory / "capture-manifest.json").relative_to(ROOT)
            ),
            "sha256": file_sha256(final_raw_directory / "capture-manifest.json"),
        },
        "capture_started_at_utc": capture_started_at,
        "capture_completed_at_utc": capture_completed_at,
        "capability_preflight": preflight_result["capability_audit"],
        "live_run_duration_seconds": round(time.monotonic() - live_run_started, 3),
        "runner_sha256": file_sha256(Path(__file__)),
        "case_results": entries,
        "exports": [
            {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}
            for path in _paper_export_paths()
        ],
    }
    write_json(RESULTS / "manifest.json", manifest)


def _capability_preflight_from_completed_raw(
    raw_by_case: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    baseline = raw_by_case[CASES[0]]["capability_audit"]
    if any(
        raw_by_case[case_name]["capability_audit"] != baseline for case_name in CASES
    ):
        raise ValueError("capability audit drifted within the completed three-case run")
    snapshots: dict[str, list[dict[str, Any]]] = {}
    for case_name in CASES:
        primary_runs = [
            run
            for run in raw_by_case[case_name]["runs"]
            if run["run_role"] == "primary_aggregate"
        ]
        if len(primary_runs) != 1:
            raise ValueError(f"{case_name}: expected one primary aggregate run")
        snapshots[case_name] = [
            {
                "qualified_source": route["qualified_source"],
                "aggregate_sources": _route_aggregate_sources(route),
                "state": _route_state(route),
            }
            for route in primary_runs[0]["routes"]
        ]
    route_counts = {len(rows) for rows in snapshots.values()}
    if len(route_counts) != 1:
        raise ValueError("qualified aggregate route count drifted across cases")
    return {
        **baseline,
        "aggregate_route_snapshots": snapshots,
        "qualified_aggregate_execution_route_count": route_counts.pop(),
    }


def report_completed_capture() -> None:
    """Build derived reports from the immutable completed capture without network I/O."""
    identity = verify_release_identity()
    _assert_final_release_binding(identity)
    capture_directory = RAW / identity["package_version"]
    capture_manifest_path = capture_directory / "capture-manifest.json"
    if not capture_manifest_path.is_file() and not FORMAL_CAPTURE_ENABLED:
        raise RuntimeError(FORMAL_CAPTURE_PAUSE_REASON)
    capture_manifest = load_json(capture_manifest_path)
    full_run_id = capture_manifest.get("full_run_id")
    runtime_distribution = _runtime_distribution_audit()
    if (
        capture_manifest.get("schema_version") != "matrouter.paper-capture-manifest/1"
        or capture_manifest.get("status") != "complete_immutable_three_case_capture"
        or not isinstance(full_run_id, str)
        or not full_run_id
        or capture_manifest.get("protocol_version") != PROTOCOL_VERSION
        or capture_manifest.get("release_binding") != identity
        or capture_manifest.get("runtime_distribution") != runtime_distribution
        or capture_manifest.get("case_order") != list(CASES)
        or capture_manifest.get("all_cases_captured_once") is not True
        or capture_manifest.get("selective_rerun") is not False
    ):
        raise ValueError("report requires one completed immutable 0.10.2 capture")
    for captured_file in capture_manifest.get("files", []):
        path = capture_directory / captured_file["path"]
        if (
            path.parent != capture_directory
            or file_sha256(path) != captured_file["sha256"]
        ):
            raise ValueError(f"raw capture file drift: {captured_file['path']}")

    raw_paths = _planned_raw_paths(identity)
    raw_by_case = {case_name: load_json(raw_paths[case_name]) for case_name in CASES}
    results: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for case_name in CASES:
        raw = raw_by_case[case_name]
        result_path = CASE_RESULTS / f"{case_name}.json"
        result = load_json(result_path)
        if (
            raw.get("schema_version") != "matrouter.paper-live-capture/8"
            or raw.get("full_run_id") != full_run_id
            or raw.get("case_name") != case_name
            or raw.get("release_binding") != identity
            or result.get("schema_version") != "matrouter.paper-case-result/14"
            or result.get("full_run_id") != full_run_id
            or result.get("case_name") != case_name
        ):
            raise ValueError(f"{case_name}: completed capture/result binding mismatch")
        replayed = replay_case(case_name, raw_paths[case_name])
        if canonical_bytes(result["evidence_bundles"]) != canonical_bytes(replayed):
            raise ValueError(f"{case_name}: completed result does not replay from raw")
        spec = case_spec(case_name)
        if result.get("task_spec") != spec:
            raise ValueError(f"{case_name}: completed result case-spec drift")
        methods = _derive_explicit_methods(
            case_name, replayed, spec, result["explicit_methods"]
        )
        result["evidence_bundles"] = replayed
        result["explicit_methods"] = methods
        result["material_landscape"] = _material_landscape_trace(result, spec)
        result["unresolved_product_blockers"] = _diagnose_case_product_blockers(result)
        result["paper_results_eligible"] = _case_paper_eligible(result)
        result["paper_result_status"] = _paper_result_status(result)
        result["case_interpretation"] = _interpretation(
            result, spec, result["coverage_matrix"], methods
        )
        write_json(result_path, result)
        results.append(result)
        coverage.extend(result["coverage_matrix"])

    export_results(results, coverage)
    write_product_blockers(results)
    write_internal_protocol_review(results, raw_paths)
    paper_results_eligible = all(
        result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
        for result in results
    ) and all(result["paper_results_eligible"] for result in results)
    entries = []
    for result in results:
        case_name = result["case_name"]
        raw_path = raw_paths[case_name]
        result_path = CASE_RESULTS / f"{case_name}.json"
        entries.append(
            {
                "case_name": case_name,
                "raw_path": str(raw_path.relative_to(ROOT)),
                "raw_sha256": file_sha256(raw_path),
                "result_path": str(result_path.relative_to(ROOT)),
                "result_sha256": file_sha256(result_path),
                "bundle_ids": [bundle["bundle_id"] for bundle in _case_bundles(result)],
                "shared_discovery_ledger": result["shared_discovery_ledger"],
                "case_spec_sha256": file_sha256(ROOT / "cases" / f"{case_name}.json"),
                "paper_result_status": result["paper_result_status"],
            }
        )
    started_at = capture_manifest["capture_started_at_utc"]
    completed_at = capture_manifest["capture_completed_at_utc"]
    duration = (
        datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
    ).total_seconds()
    manifest = {
        "schema_version": "matrouter.paper-manifest/16",
        "full_run_id": full_run_id,
        "experiment_id": experiment_id(identity),
        "status": (
            "three_case_frozen_protocol_complete"
            if paper_results_eligible
            else "three_case_frozen_protocol_run_ineligible"
        ),
        "case_count": 3,
        "paper_results_eligible": paper_results_eligible,
        "paper_results_eligibility_semantics": PAPER_ELIGIBILITY_SEMANTICS,
        "ineligibility_reasons": (
            []
            if paper_results_eligible
            else [
                f"{result['case_name']} did not meet its preregistered case-level eligibility condition or has an unresolved product blocker."
                for result in results
                if not result["paper_results_eligible"]
            ]
        ),
        "protocol_version": PROTOCOL_VERSION,
        "research_questions": COMMON_RESEARCH_QUESTIONS,
        "shared_discovery_policy": SHARED_DISCOVERY_POLICY,
        "rq3_method_applicability": {
            result["case_name"]: result["rq3_method_applicability"]
            for result in results
        },
        "core_boundary": "MatRouter routes source-qualified evidence and exact method inputs; the Agent builds the case-specific material landscape and scientific handoff.",
        "reference_assessments_enabled": False,
        "release_identity": identity,
        "runtime_distribution": runtime_distribution,
        "raw_capture_manifest": {
            "path": str(capture_manifest_path.relative_to(ROOT)),
            "sha256": file_sha256(capture_manifest_path),
        },
        "capture_started_at_utc": started_at,
        "capture_completed_at_utc": completed_at,
        "capability_preflight": _capability_preflight_from_completed_raw(raw_by_case),
        "live_run_duration_seconds": round(duration, 3),
        "runner_sha256": file_sha256(Path(__file__)),
        "case_results": entries,
        "exports": [
            {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}
            for path in _paper_export_paths()
        ],
    }
    write_json(RESULTS / "manifest.json", manifest)
    print(
        canonical_json(
            {
                "full_run_id": full_run_id,
                "status": manifest["status"],
                "paper_results_eligible": paper_results_eligible,
                "case_count": len(results),
            }
        )
    )


def replay_case(case_name: str, raw_path: Path | None = None) -> list[dict[str, Any]]:
    from matrouter._evidence_acquisition_contracts import EvidenceAcquisitionResult
    from matrouter.evidence_assembly import (
        AcquisitionBundleAssemblyRequest,
        assemble_acquired_evidence_bundle,
    )
    from matrouter.evidence_contracts import (
        EvidenceBundle,
        EvidenceRequirement,
        RouteCandidate,
    )

    if raw_path is None:
        manifest = load_json(RESULTS / "manifest.json")
        entry = next(
            row for row in manifest["case_results"] if row["case_name"] == case_name
        )
        raw_path = ROOT / entry["raw_path"]
    raw = load_json(raw_path)
    capsules: list[dict[str, Any]] = []
    role_names = {
        "target_followup": "target_followup",
        "thermochemical": "thermochemical",
    }
    primary_run = next(
        run for run in raw["runs"] if run["run_role"] == "primary_aggregate"
    )
    primary_requirements = tuple(
        EvidenceRequirement.model_validate(wire(row))
        for row in primary_run["requirements"]
    )
    primary_routes = tuple(
        RouteCandidate.model_validate(wire(row)) for row in primary_run["routes"]
    )
    primary_acquisitions = tuple(
        EvidenceAcquisitionResult.model_validate(wire(value))
        for value in primary_run["acquisitions"]
    )
    cumulative_requirements = list(primary_requirements)
    cumulative_routes = list(primary_routes)
    cumulative_acquisitions = list(primary_acquisitions)
    for run in raw["runs"]:
        if run["run_role"] == "primary_aggregate":
            bundle = EvidenceBundle.model_validate(wire(run["canonical_bundle"]))
            capsules.append(
                {
                    "bundle_role": "primary_aggregate",
                    "qualified_source_route": None,
                    "run_capacity": run["run_capacity"],
                    "evidence_bundle": bundle.model_dump(
                        mode="json", exclude_computed_fields=True
                    ),
                }
            )
            continue
        closure_requirements = tuple(
            EvidenceRequirement.model_validate(wire(row)) for row in run["requirements"]
        )
        closure_routes = tuple(
            RouteCandidate.model_validate(wire(row)) for row in run["routes"]
        )
        closure_acquisitions = tuple(
            EvidenceAcquisitionResult.model_validate(wire(row))
            for row in run["acquisitions"]
        )
        cumulative_requirements.extend(closure_requirements)
        cumulative_routes.extend(closure_routes)
        cumulative_acquisitions.extend(closure_acquisitions)
        bundle = assemble_acquired_evidence_bundle(
            AcquisitionBundleAssemblyRequest(
                requirements=tuple(cumulative_requirements),
                routes=tuple(cumulative_routes),
                acquisitions=tuple(cumulative_acquisitions),
            )
        )
        capsules.append(
            {
                "bundle_role": role_names[run["run_role"]],
                "qualified_source_route": run["qualified_source_route"],
                "run_capacity": run["run_capacity"],
                "evidence_bundle": bundle.model_dump(
                    mode="json", exclude_computed_fields=True
                ),
            }
        )
    return capsules


def refresh_derived_outputs() -> None:
    from matrouter.evidence_contracts import EvidenceBundle

    manifest = load_json(RESULTS / "manifest.json")
    if (
        manifest.get("schema_version") != "matrouter.paper-manifest/16"
        or manifest.get("release_identity", {}).get("package_version") != "0.10.2"
        or not manifest.get("full_run_id")
    ):
        raise ValueError(
            "refresh accepts only a completed 0.10.2 capture; legacy Bundle outputs have no compatibility path"
        )
    manifest_entries = {row["case_name"]: row for row in manifest["case_results"]}
    results: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for case_name in CASES:
        path = CASE_RESULTS / f"{case_name}.json"
        result = load_json(path)
        raw = load_json(ROOT / manifest_entries[case_name]["raw_path"])
        spec = case_spec(case_name)
        bundle_capsules = replay_case(case_name)
        for capsule in bundle_capsules:
            EvidenceBundle.model_validate(wire(capsule["evidence_bundle"]))
        methods = _derive_explicit_methods(
            case_name, bundle_capsules, spec, result["explicit_methods"]
        )
        actual_strategy, protocol_conformance = _capture_protocol_status(raw, spec)
        result["schema_version"] = "matrouter.paper-case-result/14"
        result["full_run_id"] = raw["full_run_id"]
        result["protocol_version"] = PROTOCOL_VERSION
        result["research_questions"] = COMMON_RESEARCH_QUESTIONS
        result["shared_discovery_policy"] = SHARED_DISCOVERY_POLICY
        result["rq3_method_applicability"] = spec["rq3_method_applicability"]
        result["scientific_question"] = spec["scientific_question"]
        result["task_spec"] = spec
        result["actual_retrieval_strategy"] = actual_strategy
        result["protocol_conformance"] = protocol_conformance
        result["evidence_bundles"] = bundle_capsules
        aggregate_capsules = [
            capsule
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "primary_aggregate"
        ]
        if len(aggregate_capsules) != 1:
            raise ValueError(f"{case_name}: expected one primary aggregate Bundle")
        aggregate_bundle = aggregate_capsules[0]["evidence_bundle"]
        result["primary_result_bundle_id"] = aggregate_bundle["bundle_id"]
        result["aggregate"] = _aggregate_summary(aggregate_bundle)
        result["shared_discovery_ledger"] = _shared_discovery_summary(
            aggregate_bundle, aggregate_capsules[0]["run_capacity"]
        )
        result["explicit_methods"] = methods
        result["material_landscape"] = _material_landscape_trace(result, spec)
        result["unresolved_product_blockers"] = _diagnose_case_product_blockers(result)
        result["paper_results_eligible"] = _case_paper_eligible(result)
        result["paper_results_eligibility_semantics"] = PAPER_ELIGIBILITY_SEMANTICS
        result["paper_result_status"] = _paper_result_status(result)
        result["case_interpretation"] = _interpretation(
            result, spec, result["coverage_matrix"], methods
        )
        write_json(path, result)
        results.append(result)
        coverage.extend(result["coverage_matrix"])
    export_results(results, coverage)
    write_product_blockers(results)
    write_internal_protocol_review(results)
    manifest["schema_version"] = "matrouter.paper-manifest/16"
    identity = load_json(IDENTITY_PATH)
    manifest["experiment_id"] = experiment_id(identity)
    paper_results_eligible = all(
        result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
        for result in results
    ) and all(result["paper_results_eligible"] for result in results)
    manifest["status"] = (
        "three_case_frozen_protocol_complete"
        if paper_results_eligible
        else "three_case_frozen_protocol_run_ineligible"
    )
    manifest["protocol_version"] = PROTOCOL_VERSION
    manifest["research_questions"] = COMMON_RESEARCH_QUESTIONS
    manifest["shared_discovery_policy"] = SHARED_DISCOVERY_POLICY
    manifest["core_boundary"] = (
        "MatRouter routes source-qualified evidence and exact method inputs; the Agent "
        "builds the case-specific material landscape and scientific handoff."
    )
    manifest["rq3_method_applicability"] = {
        result["case_name"]: result["rq3_method_applicability"] for result in results
    }
    manifest["paper_results_eligible"] = paper_results_eligible
    manifest["paper_results_eligibility_semantics"] = PAPER_ELIGIBILITY_SEMANTICS
    manifest["ineligibility_reasons"] = (
        []
        if paper_results_eligible
        else [
            f"{result['case_name']} did not meet its preregistered case-level eligibility condition or has an unresolved product blocker."
            for result in results
            if not result["paper_results_eligible"]
        ]
    )
    manifest["release_identity"] = identity
    manifest["runner_sha256"] = file_sha256(Path(__file__))
    for entry in manifest["case_results"]:
        result = next(row for row in results if row["case_name"] == entry["case_name"])
        entry["paper_result_status"] = result["paper_result_status"]
        entry["shared_discovery_ledger"] = result["shared_discovery_ledger"]
        entry["result_sha256"] = file_sha256(ROOT / entry["result_path"])
        entry["case_spec_sha256"] = file_sha256(
            ROOT / "cases" / f"{entry['case_name']}.json"
        )
        entry["bundle_ids"] = [bundle["bundle_id"] for bundle in _case_bundles(result)]
    manifest["exports"] = [
        {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}
        for path in _paper_export_paths()
    ]
    write_json(RESULTS / "manifest.json", manifest)


def validate() -> None:
    from matrouter.evidence_contracts import EvidenceBundle

    identity = verify_release_identity()
    current_specs = {case_name: case_spec(case_name) for case_name in CASES}
    if not FORMAL_CAPTURE_ENABLED:
        active_capture = RAW / identity["package_version"]
        if active_capture.exists():
            raise ValueError(
                "formal capture is paused but an active release-bound raw directory exists"
            )
        staging_root = RAW / ".staging"
        if staging_root.exists() and any(staging_root.iterdir()):
            raise ValueError(
                "formal capture is paused but a staged capture still exists"
            )
        manifest_path = RESULTS / "manifest.json"
        if manifest_path.is_file():
            existing_manifest = load_json(manifest_path)
            if (
                existing_manifest.get("release_identity", {}).get("package_version")
                == identity["package_version"]
            ):
                raise ValueError(
                    "formal capture is paused but results still claim the configured active release"
                )
        invalidated = list(
            (RAW / "invalidated" / identity["package_version"]).glob("*.json")
        )
        if not invalidated:
            raise ValueError("paused capture state lacks an invalidation audit marker")
        return
    if not (RESULTS / "manifest.json").is_file():
        raise FileNotFoundError(
            "current-protocol result manifest has not been generated; final release-bound run is pending"
        )
    manifest = load_json(RESULTS / "manifest.json")
    if manifest.get("experiment_id") != experiment_id(identity):
        raise ValueError(
            "current-protocol experiment identity mismatch; final release-bound artifacts are pending"
        )
    if manifest.get("release_identity") != identity:
        raise ValueError(
            "current-protocol release identity mismatch; final release-bound artifacts are pending"
        )
    if manifest.get("case_count") != 3:
        raise ValueError("manifest must declare exactly three cases")
    if manifest.get("schema_version") != "matrouter.paper-manifest/16":
        raise ValueError(
            "manifest schema mismatch; the forward protocol requires a fresh full "
            "release-bound acquisition and must not refresh frozen legacy results"
        )
    full_run_id = manifest.get("full_run_id")
    if not isinstance(full_run_id, str) or not full_run_id:
        raise ValueError("manifest full-run identity is missing")
    runtime_distribution = _runtime_distribution_audit()
    if manifest.get("runtime_distribution") != runtime_distribution:
        raise ValueError("manifest runtime distribution audit drift")
    expected_capture_manifest_path = (
        RAW / identity["package_version"] / "capture-manifest.json"
    )
    capture_manifest_ref = manifest.get("raw_capture_manifest") or {}
    if capture_manifest_ref.get("path") != str(
        expected_capture_manifest_path.relative_to(ROOT)
    ) or capture_manifest_ref.get("sha256") != file_sha256(
        expected_capture_manifest_path
    ):
        raise ValueError("raw capture-manifest binding drift")
    capture_manifest = load_json(expected_capture_manifest_path)
    if (
        capture_manifest.get("schema_version") != "matrouter.paper-capture-manifest/1"
        or capture_manifest.get("status") != "complete_immutable_three_case_capture"
        or capture_manifest.get("full_run_id") != full_run_id
        or capture_manifest.get("protocol_version") != PROTOCOL_VERSION
        or capture_manifest.get("release_binding") != identity
        or capture_manifest.get("runtime_distribution") != runtime_distribution
        or capture_manifest.get("case_order") != list(CASES)
        or capture_manifest.get("all_cases_captured_once") is not True
        or capture_manifest.get("selective_rerun") is not False
    ):
        raise ValueError("raw capture manifest is not the completed full-run contract")
    capture_directory = expected_capture_manifest_path.parent
    for captured_file in capture_manifest.get("files", []):
        path = capture_directory / captured_file["path"]
        if (
            path.parent != capture_directory
            or file_sha256(path) != captured_file["sha256"]
        ):
            raise ValueError(f"raw capture file drift: {captured_file['path']}")
    protocol_snapshot = load_json(capture_directory / "protocol.json")
    if (
        protocol_snapshot.get("schema_version") != "matrouter.paper-capture-protocol/1"
        or protocol_snapshot.get("full_run_id") != full_run_id
        or protocol_snapshot.get("release_binding") != identity
        or protocol_snapshot.get("runtime_distribution") != runtime_distribution
        or protocol_snapshot.get("case_order") != list(CASES)
        or protocol_snapshot.get("selective_rerun_permitted") is not False
    ):
        raise ValueError("frozen capture protocol drift")
    capture_log = load_json(capture_directory / "run-log.json")
    if (
        capture_log.get("schema_version") != "matrouter.paper-capture-log/1"
        or capture_log.get("full_run_id") != full_run_id
        or not capture_log.get("events")
        or capture_log["events"][-1].get("event") != "full_capture_completed"
    ):
        raise ValueError("structured full-run log is incomplete")
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("manifest protocol identity mismatch")
    if manifest.get("research_questions") != COMMON_RESEARCH_QUESTIONS:
        raise ValueError("manifest research-question mismatch")
    if manifest.get("shared_discovery_policy") != SHARED_DISCOVERY_POLICY:
        raise ValueError("manifest shared discovery policy mismatch")
    if (
        manifest.get("paper_results_eligibility_semantics")
        != PAPER_ELIGIBILITY_SEMANTICS
    ):
        raise ValueError("manifest protocol-eligibility semantics mismatch")
    if [row["case_name"] for row in manifest["case_results"]] != list(CASES):
        raise ValueError("manifest must contain exactly the three named cases")
    expected_applicability = {
        case_name: spec["rq3_method_applicability"]
        for case_name, spec in current_specs.items()
    }
    if manifest.get("rq3_method_applicability") != expected_applicability:
        raise ValueError("manifest RQ3 applicability mismatch")
    results_by_case: dict[str, dict[str, Any]] = {}
    for entry in manifest["case_results"]:
        if file_sha256(ROOT / entry["raw_path"]) != entry["raw_sha256"]:
            raise ValueError(f"{entry['case_name']}: raw capture digest drift")
        if file_sha256(ROOT / entry["result_path"]) != entry["result_sha256"]:
            raise ValueError(f"{entry['case_name']}: result digest drift")
        if (
            file_sha256(ROOT / "cases" / f"{entry['case_name']}.json")
            != entry["case_spec_sha256"]
        ):
            raise ValueError(f"{entry['case_name']}: case spec digest drift")
        result = load_json(ROOT / entry["result_path"])
        results_by_case[entry["case_name"]] = result
        raw = load_json(ROOT / entry["raw_path"])
        if (
            result.get("full_run_id") != full_run_id
            or raw.get("full_run_id") != full_run_id
        ):
            raise ValueError(f"{entry['case_name']}: full-run identity drift")
        if result.get("schema_version") != "matrouter.paper-case-result/14":
            raise ValueError(f"{entry['case_name']}: result schema mismatch")
        if result.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(f"{entry['case_name']}: result protocol mismatch")
        if raw.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(f"{entry['case_name']}: raw protocol mismatch")
        if raw.get("schema_version") != "matrouter.paper-live-capture/8":
            raise ValueError(f"{entry['case_name']}: raw capture schema mismatch")
        if any(
            run.get("run_role")
            not in {
                "primary_aggregate",
                "target_followup",
                "thermochemical",
            }
            for run in raw.get("runs", [])
        ):
            raise ValueError(f"{entry['case_name']}: unsupported run role")
        if result.get("research_questions") != COMMON_RESEARCH_QUESTIONS:
            raise ValueError(f"{entry['case_name']}: research-question mismatch")
        if result.get("shared_discovery_policy") != SHARED_DISCOVERY_POLICY:
            raise ValueError(f"{entry['case_name']}: shared discovery policy mismatch")
        if (
            result.get("paper_results_eligibility_semantics")
            != PAPER_ELIGIBILITY_SEMANTICS
        ):
            raise ValueError(
                f"{entry['case_name']}: protocol-eligibility semantics mismatch"
            )
        spec = current_specs[entry["case_name"]]
        if result.get("rq3_method_applicability") != spec["rq3_method_applicability"]:
            raise ValueError(f"{entry['case_name']}: RQ3 applicability mismatch")
        if result.get("task_spec") != spec:
            raise ValueError(f"{entry['case_name']}: active task spec mismatch")
        required_result_fields = {
            "aggregate",
            "shared_discovery_ledger",
            "primary_result_bundle_id",
            "material_landscape",
            "unresolved_product_blockers",
            "paper_results_eligible",
        }
        if not required_result_fields <= result.keys():
            raise ValueError(f"{entry['case_name']}: current protocol fields missing")
        if "stage_2_target_audit" not in result.get("protocol_conformance", {}):
            raise ValueError(f"{entry['case_name']}: Stage-2 target audit missing")
        aggregate_capsules = [
            capsule
            for capsule in result["evidence_bundles"]
            if capsule["bundle_role"] == "primary_aggregate"
        ]
        if len(aggregate_capsules) != 1:
            raise ValueError(
                f"{entry['case_name']}: expected exactly one primary aggregate"
            )
        stored = [
            EvidenceBundle.model_validate(wire(capsule["evidence_bundle"]))
            for capsule in result["evidence_bundles"]
        ]
        replayed = replay_case(entry["case_name"], ROOT / entry["raw_path"])
        if canonical_bytes(result["evidence_bundles"]) != canonical_bytes(replayed):
            raise ValueError(f"{entry['case_name']}: canonical replay mismatch")
        if [bundle.bundle_id for bundle in stored] != entry["bundle_ids"]:
            raise ValueError(f"{entry['case_name']}: bundle identity drift")
        if len(result["coverage_matrix"]) != len(raw["qualified_source_routes"]):
            raise ValueError(
                f"{entry['case_name']}: all-qualified coverage is incomplete"
            )
        if result["coverage_matrix"] != _aggregate_coverage_rows(
            entry["case_name"], aggregate_capsules[0]["evidence_bundle"]
        ):
            raise ValueError(f"{entry['case_name']}: aggregate coverage drift")
        expected_strategy, expected_conformance = _capture_protocol_status(raw, spec)
        if result["actual_retrieval_strategy"] != expected_strategy:
            raise ValueError(f"{entry['case_name']}: captured strategy mismatch")
        if result["protocol_conformance"] != expected_conformance:
            raise ValueError(f"{entry['case_name']}: protocol conformance mismatch")
        aggregate_bundle = aggregate_capsules[0]["evidence_bundle"]
        if result["primary_result_bundle_id"] != aggregate_bundle["bundle_id"]:
            raise ValueError(f"{entry['case_name']}: primary result identity drift")
        if result["aggregate"] != _aggregate_summary(aggregate_bundle):
            raise ValueError(f"{entry['case_name']}: aggregate summary drift")
        expected_shared_summary = _shared_discovery_summary(
            aggregate_bundle, aggregate_capsules[0]["run_capacity"]
        )
        if result["shared_discovery_ledger"] != expected_shared_summary:
            raise ValueError(f"{entry['case_name']}: shared discovery summary drift")
        if raw.get("shared_discovery_ledger") != expected_shared_summary:
            raise ValueError(
                f"{entry['case_name']}: raw shared discovery summary drift"
            )
        if result["material_landscape"] != _material_landscape_trace(result, spec):
            raise ValueError(f"{entry['case_name']}: material-landscape trace drift")
        trace_path = RESULTS / "case-traces" / f"{entry['case_name']}.json"
        if load_json(trace_path) != result["material_landscape"]:
            raise ValueError(f"{entry['case_name']}: case-trace export drift")
        if result["unresolved_product_blockers"] != _diagnose_case_product_blockers(
            result
        ):
            raise ValueError(f"{entry['case_name']}: product-blocker drift")
        if result["paper_results_eligible"] != _case_paper_eligible(result):
            raise ValueError(f"{entry['case_name']}: eligibility drift")
        if result.get("paper_result_status") != _paper_result_status(result):
            raise ValueError(f"{entry['case_name']}: paper-result status drift")
        if entry.get("paper_result_status") != result["paper_result_status"]:
            raise ValueError(f"{entry['case_name']}: manifest case status drift")
        if entry.get("shared_discovery_ledger") != expected_shared_summary:
            raise ValueError(
                f"{entry['case_name']}: manifest shared discovery summary drift"
            )
        bundle_item_ids = {
            item["item_id"]
            for bundle in _case_bundles(result)
            for item in bundle["evidence_items"]
        }
        method_input_ids = {
            item_id
            for method in result["explicit_methods"]
            for item_id in method["exact_input_item_ids"]
        }
        if not method_input_ids <= bundle_item_ids:
            raise ValueError(
                f"{entry['case_name']}: explicit method input is not in bundle"
            )
        if any(
            not _method_inputs_bind_declared_bundles(result, method)
            for method in result["explicit_methods"]
        ):
            raise ValueError(
                f"{entry['case_name']}: explicit method crosses exact Bundle authority"
            )
    _validate_paper_observation_export_consistency(results_by_case)
    ordered_results = [results_by_case[case_name] for case_name in CASES]
    if load_json(
        RESULTS / "source-completeness-review.json"
    ) != _source_completeness_review(ordered_results):
        raise ValueError("source-completeness-review.json export drift")
    if load_json(
        RESULTS / "rq1-rq2-shared-ledger-audit.json"
    ) != _rq1_rq2_shared_ledger_report(ordered_results):
        raise ValueError("rq1-rq2-shared-ledger-audit.json export drift")
    for export in manifest["exports"]:
        if file_sha256(ROOT / export["path"]) != export["sha256"]:
            raise ValueError(f"export digest drift: {export['path']}")
    forbidden = (str(Path.home()), str(Path("/private/tmp")))
    paths_to_scan = (
        [ROOT / row["raw_path"] for row in manifest["case_results"]]
        + [ROOT / row["result_path"] for row in manifest["case_results"]]
        + list(capture_directory.glob("*.json"))
    )
    for path in paths_to_scan:
        text = path.read_text()
        if any(value in text for value in forbidden):
            raise ValueError(f"{path}: absolute host path leaked")
        if any(
            name in text
            for name in (
                "MATROUTER_MP_API_KEY=",
                "MATROUTER_MPDS_API_KEY=",
                "MATROUTER_MG_API_KEY=",
            )
        ):
            raise ValueError(f"{path}: secret assignment leaked")


def smoke() -> None:
    audit = preflight()["capability_audit"]
    print(
        canonical_json(
            {
                "declared_source_authority_count": audit[
                    "declared_source_authority_count"
                ],
                "qualified_aggregate_execution_route_count": audit[
                    "qualified_aggregate_execution_route_count"
                ],
                "optimade_child_route_count": audit["optimade_child_route_count"],
                "requires_configuration_pair_count": audit[
                    "requires_configuration_pair_count"
                ],
            }
        )
    )


def main() -> None:
    load_private_environment()
    os.environ.setdefault("MATROUTER_CACHE_DIR", ".runtime-cache")
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    sub.add_parser("validate")
    sub.add_parser("smoke")
    sub.add_parser("preflight")
    sub.add_parser("verify")
    sub.add_parser("refresh")
    sub.add_parser("report")
    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("--case", choices=CASES, required=True)
    args = parser.parse_args()
    if args.command == "run":
        run_all()
    elif args.command == "validate":
        validate()
    elif args.command in {"smoke", "preflight"}:
        smoke()
    elif args.command == "verify":
        validate()
        if FORMAL_CAPTURE_ENABLED:
            for case_name in CASES:
                replay_case(case_name)
    elif args.command == "refresh":
        refresh_derived_outputs()
    elif args.command == "report":
        report_completed_capture()
    else:
        print(
            canonical_json(
                [
                    capsule["evidence_bundle"]["bundle_id"]
                    for capsule in replay_case(args.case)
                ]
            )
        )


if __name__ == "__main__":
    main()
