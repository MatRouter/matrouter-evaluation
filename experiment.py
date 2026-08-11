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
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".runtime-cache" / "matplotlib"))
REPOSITORY_ROOT = ROOT
IDENTITY_PATH = ROOT / "product-identity.release.json"
CASES = ("mos2-band-gap", "lifepo4-stability", "bi2se3-topology")
PROTOCOL_VERSION = "matrouter.paper-three-case-protocol"
FINAL_RELEASE_BINDING = {
    "package_version": "0.9.2",
    "public_VERSION": "0.9.2",
    "release_tag": "v0.9.2",
}
COMMON_RESEARCH_QUESTIONS = {
    "RQ1": "Within the declared catalog, configuration, scope, and budgets, does one all-qualified aggregate attempt every capability-matched route and preserve each typed outcome and RecordCompleteness?",
    "RQ2": "What material-data landscape do the preregistered non-selective per-route source-record exhaustion shards provide for the case—sources, data categories, scientific contexts, specialist data, completeness, and explicit gaps—and how does that landscape guide the next research step?",
    "RQ3": "Can an Agent use the aggregate to locate preregistered exact source-bound records and artifacts for explicit lightweight methods, while making unsupported heavy calculations an explicit external handoff rather than a proxy result?",
}
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
CASE_RESULTS = RESULTS / "cases"
ARTIFACTS = RESULTS / "artifacts"

SOURCE_RECORD_SAFETY_LIMIT = 60
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
DISCOVERY_RETRIEVAL = {
    "source_scope": "all_qualified",
    "record_scope": "exhaust_upstream",
    "max_pages": 100,
    "max_elapsed_seconds": 300.0,
    "max_bytes": 100_000_000,
}
THERMOCHEMICAL_LIMIT = 2000
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
    "RQ1 uses one aggregate_source_records call for bounded parallel cross-source execution over "
    "all parsed qualified routes (at most eight workers), preserves stable-order aggregation, "
    "and returns one primary EvidenceBundle. Per-source pagination remains sequential. The public "
    "512-item/16-MB capacity is shared by execution route; capacity and safety stops remain typed "
    "partial or truncated. All qualified routes are attempted, but not every upstream record is "
    "claimed retrieved."
)
RQ2_SHARD_POLICY = {
    "selection": "every_ready_primary_search_materials_execution_route_in_stable_exact_route_order",
    "source_scope": "selected",
    "record_scope": "exhaust_upstream",
    "record_limit": "begin_evidence_run.capacity.max_single_source_record_items",
    "max_pages_per_route": DISCOVERY_RETRIEVAL["max_pages"],
    "max_elapsed_seconds_per_route": DISCOVERY_RETRIEVAL["max_elapsed_seconds"],
    "max_normalized_bytes_per_route": DISCOVERY_RETRIEVAL["max_bytes"],
    "bundle_policy": "one_bounded_evidence_run_and_bundle_per_exact_execution_route",
}
RQ2_SHARD_SCOPE = (
    "RQ2 uses one independent selected-source exhaust-upstream Evidence run and Bundle for every "
    "ready primary search_materials execution route in stable exact-route order. Each run takes "
    "its record limit from begin_evidence_run.capacity.max_single_source_record_items and retains "
    "the common page, time, and byte ceilings. Records remain source-qualified and unmerged; "
    "complete inventory eligibility requires every shard to be complete or verified empty."
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
        RouteCandidate,
        ScientificArtifactItem,
        StructureItem,
        ThermochemicalEntrySetItem,
    )

    identity = load_json(IDENTITY_PATH)
    installed_distribution = distribution("matrouter")
    if version("matrouter") != identity["package_version"]:
        raise ValueError("installed MatRouter version mismatch")
    if matrouter.VERSION != identity["public_VERSION"]:
        raise ValueError("installed MatRouter public VERSION mismatch")
    metadata = identity["distribution_metadata"]
    if installed_distribution.metadata["Name"] != metadata["name"]:
        raise ValueError("installed distribution name mismatch")
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
        ThermochemicalEntrySetItem,
    ):
        if retired_identity_fields & model.model_fields.keys():
            raise ValueError(
                f"{model.__name__} retains a retired product identity field"
            )
    route_contract = identity["route_contract"]
    if "output_sources" not in RouteCandidate.model_fields:
        raise ValueError("installed RouteCandidate lacks required output_sources")
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
    if spec.get("schema_version") != "matrouter.paper-case-spec/11":
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
        "record_safety_limit_per_route": SOURCE_RECORD_SAFETY_LIMIT,
        "max_pages_per_route": DISCOVERY_RETRIEVAL["max_pages"],
        "max_elapsed_seconds_per_route": DISCOVERY_RETRIEVAL["max_elapsed_seconds"],
        "max_normalized_bytes_per_route": DISCOVERY_RETRIEVAL["max_bytes"],
        "public_bundle_item_limit": 512,
        "public_bundle_canonical_byte_limit": 16_000_000,
    }
    if spec.get("stage_1") != expected_stage_1:
        raise ValueError(f"{case_name}: Stage 1 differs from the common frozen budget")
    if spec.get("rq2_source_record_exhaustion_shards") != RQ2_SHARD_POLICY:
        raise ValueError(f"{case_name}: RQ2 exhaustion-shard policy mismatch")
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
    aggregate_identities = [
        json.loads(item["record_json"]) for item in aggregate_records
    ]
    aggregate_discovered = {
        (record.get("source"), record.get("source_id"))
        for record in aggregate_identities
    }
    target_runs = [row for row in raw["runs"] if row["run_role"] == "target_followup"]
    discovery_acquisitions = [
        acquisition
        for run in target_runs
        for acquisition in run["acquisitions"]
        if acquisition["route"]["operation"] == "search_materials"
    ]
    discovered = {
        (ref["source"], ref["source_id"])
        for acquisition in discovery_acquisitions
        for ref in acquisition.get("record_refs", [])
    }
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
        found_for_followup = (source, source_id) in discovered
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
            route_rows.append(
                {
                    **expected,
                    "requirement_count": len(matching_requirements),
                    "ready_route_count": sum(
                        row["state"] == "ready" for row in matching_routes
                    ),
                    "executed_count": len(matching_acquisitions),
                    "succeeded_count": sum(
                        row["outcome_draft"]["status"] == "succeeded"
                        for row in matching_acquisitions
                    ),
                    "failed_count": sum(
                        row["outcome_draft"]["status"] == "failed"
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
                "found_in_target_followup": found_for_followup,
                "enrichment_routes": route_rows,
                "status": (
                    "missing"
                    if not (found_in_aggregate or found_for_followup)
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
            row["found_in_primary_aggregate"] or row["found_in_target_followup"]
            for row in target_rows
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
        "passed": (
            all(
                row["status"] in {"present_no_enrichment", "succeeded"}
                for row in target_rows
            )
            and executed_route_count == expected_route_count
            and succeeded_route_count == expected_route_count
        ),
    }


def _rq2_shard_capture_audit(raw: dict[str, Any]) -> dict[str, Any]:
    primary_runs = [
        run for run in raw["runs"] if run["run_role"] == "primary_aggregate"
    ]
    expected_routes = (
        sorted(
            route["qualified_source"]
            for route in primary_runs[0].get("routes", [])
            if route["state"] == "ready" and route["operation"] == "search_materials"
        )
        if len(primary_runs) == 1
        else []
    )
    shard_runs = [
        run
        for run in raw["runs"]
        if run["run_role"] == "source_record_exhaustion_shard"
    ]
    actual_routes = [run["qualified_source_route"] for run in shard_runs]
    run_checks = []
    for run in shard_runs:
        source = run["qualified_source_route"]
        requirements = run["requirements"]
        routes = run["routes"]
        acquisitions = run["acquisitions"]
        capacity = run["run_capacity"]
        requirement = requirements[0] if len(requirements) == 1 else {}
        constraints = requirement.get("operational_constraints") or {}
        retrieval = constraints.get("retrieval") or {}
        passed = (
            len(requirements) == 1
            and requirement.get("evidence_kind") == "source_record"
            and constraints.get("sources") == [source]
            and constraints.get("limit")
            == capacity.get("max_single_source_record_items")
            and retrieval.get("source_scope") == "selected"
            and retrieval.get("record_scope") == "exhaust_upstream"
            and retrieval.get("max_pages") == DISCOVERY_RETRIEVAL["max_pages"]
            and retrieval.get("max_elapsed_seconds")
            == DISCOVERY_RETRIEVAL["max_elapsed_seconds"]
            and retrieval.get("max_bytes") == DISCOVERY_RETRIEVAL["max_bytes"]
            and len(routes) == 1
            and routes[0].get("qualified_source") == source
            and routes[0].get("operation") == "search_materials"
            and routes[0].get("state") == "ready"
            and len(acquisitions) == 1
            and acquisitions[0].get("route", {}).get("qualified_source") == source
            and acquisitions[0].get("outcome_draft") is not None
        )
        run_checks.append({"source": source, "passed": passed})
    summary = raw.get("rq2_source_record_exhaustion") or {}
    passed = (
        actual_routes == expected_routes
        and all(row["passed"] for row in run_checks)
        and summary.get("shard_routes") == expected_routes
        and summary.get("shard_count") == len(expected_routes)
        and summary.get("all_ready_routes_sharded") is True
    )
    return {
        "expected_ready_route_count": len(expected_routes),
        "shard_run_count": len(shard_runs),
        "expected_routes": expected_routes,
        "actual_routes": actual_routes,
        "run_checks": run_checks,
        "complete_inventory_eligible": summary.get(
            "complete_inventory_eligible", False
        ),
        "gap_count": summary.get("gap_count"),
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
            and aggregate_summary["source_outcome_count"]
            == aggregate_summary["qualified_route_count"]
            and aggregate_summary["all_qualified_routes_have_typed_outcome"]
            and aggregate_summary["real_cross_source_records"]
        )
        rq2_shard_audit = _rq2_shard_capture_audit(raw)
        conformance = {
            "single_primary_all_route_aggregate": aggregate_closed,
            "primary_aggregate_summary": aggregate_summary,
            "run_roles_valid": all(
                row["run_role"]
                in {
                    "primary_aggregate",
                    "source_record_exhaustion_shard",
                    "target_followup",
                    "thermochemical",
                }
                for row in raw["runs"]
            ),
            "rq2_source_record_exhaustion_shards": rq2_shard_audit,
            "stage_2_preregistered_exact_targets": True,
            "capture_eligible_under_frozen_protocol": aggregate_closed
            and rq2_shard_audit["passed"],
            "reason": None,
        }
        if spec is not None:
            audit = _stage2_target_audit(raw, spec)
            conformance["stage_2_target_audit"] = audit
            conformance["capture_eligible_under_frozen_protocol"] = (
                aggregate_closed
                and conformance["run_roles_valid"]
                and rq2_shard_audit["passed"]
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
    limit: int = SOURCE_RECORD_SAFETY_LIMIT,
    all_qualified: bool = False,
    filters: tuple[Any, ...] = (),
) -> Any:
    from matrouter.evidence_contracts import OperationalConstraints
    from matrouter.retrieval import RetrievalStrategy

    retrieval = (
        RetrievalStrategy(**DISCOVERY_RETRIEVAL)
        if all_qualified
        else RetrievalStrategy(
            source_scope="selected",
            record_scope="exhaust_upstream",
            max_pages=DISCOVERY_RETRIEVAL["max_pages"],
            max_elapsed_seconds=DISCOVERY_RETRIEVAL["max_elapsed_seconds"],
            max_bytes=DISCOVERY_RETRIEVAL["max_bytes"],
        )
    )
    return OperationalConstraints(
        sources=() if all_qualified else sources,
        limit=limit,
        retrieval=retrieval,
        filters=filters,
    )


def _create_requirement(
    tools: Any,
    run_id: str,
    *,
    label: str,
    subject: Any,
    kind: str,
    use: str,
    constraints: Any,
) -> Any:
    from matrouter.tools.evidence import CreateEvidenceRequirementRequest

    return tools.create_evidence_requirement(
        CreateEvidenceRequirementRequest(
            evidence_run_id=run_id,
            label=label,
            subject_scope=subject,
            evidence_kind=kind,
            evidence_use=use,
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
        label=f"{case_name}-{_safe_label(source)}-{record_label}-{kind}",
        subject=_subject(formula=formula),
        kind=kind,
        use=f"Exact {kind} evidence for the acquired {source}/{record_ref.source_id} record.",
        constraints=_constraints(sources=(source,), limit=1),
    )
    requirements.append(requirement)
    candidates = _route(tools, run_id, requirement)
    routes.extend(candidates)
    selected = [
        route
        for route in candidates
        if route.operation == operation and route.state == "ready"
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
    return [item for item in bundle["items"] if item["item_kind"] == item_kind]


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


def _rq2_source_record_bundles(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        capsule["evidence_bundle"]
        for capsule in result["evidence_bundles"]
        if capsule["bundle_role"] == "source_record_exhaustion_shard"
    ]


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

    outcomes = [item["outcome"] for item in _bundle_items(bundle, "source_outcome")]
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
    outcome_rows = [
        {
            "source": outcome["source"],
            "operation": outcome["operation"],
            "status": outcome["status"],
            "reason_code": outcome["reason_code"],
            "record_count": outcome["record_count"],
            "record_completeness": outcome.get("record_completeness"),
        }
        for outcome in sorted(
            outcomes, key=lambda row: (row["source"], row["operation"])
        )
    ]
    completeness_counts = Counter(
        (outcome.get("record_completeness") or {}).get("state", "missing")
        for outcome in outcomes
    )
    capacity_limitations = [
        row
        for row in outcome_rows
        if (row.get("record_completeness") or {}).get("state") == "truncated"
        or row["reason_code"] == "evidence_run_capacity_exceeded"
    ]
    qualified_sources = sorted(row["qualified_source"] for row in bundle["routes"])
    outcome_sources = sorted(row["source"] for row in outcomes)
    all_routes_have_typed_outcome = (
        len(outcome_sources) == len(set(outcome_sources))
        and outcome_sources == qualified_sources
    )
    return {
        "bundle_id": bundle["bundle_id"],
        "semantics": "The one primary agent-facing EvidenceBundle produced by aggregate_source_records through bounded parallel cross-source execution with at most eight workers and stable-order aggregation; per-source pagination remains sequential.",
        "execution_routes": [
            {
                "qualified_source": row["qualified_source"],
                "output_sources": row.get("output_sources", []),
                "state": row["state"],
            }
            for row in bundle["routes"]
        ],
        "qualified_route_count": len(bundle["routes"]),
        "ready_route_count": sum(row["state"] == "ready" for row in bundle["routes"]),
        "attempted_route_count": len(outcomes),
        "source_outcome_count": len(outcomes),
        "all_qualified_routes_have_typed_outcome": all_routes_have_typed_outcome,
        "source_record_count": len(source_records),
        "source_record_sources": record_sources,
        "source_record_source_count": len(record_sources),
        "source_record_providers": record_providers,
        "source_record_provider_count": len(record_providers),
        "source_record_provider_identity_complete": provider_identity_complete,
        "real_cross_source_records": real_cross_source_records,
        "status_counts": dict(
            sorted(Counter(row["status"] for row in outcomes).items())
        ),
        "record_completeness_counts": dict(sorted(completeness_counts.items())),
        "capacity_limitations": capacity_limitations,
        "source_outcomes": outcome_rows,
        "materials_galaxy_parent_outcome_semantics": "The provider-level MaterialsGalaxy outcome describes one combined summary query. Child dataset provenance on returned records does not establish a separate child execution outcome, success, or exhaustive empty result.",
    }


def _property_occurrences(
    bundle: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """Yield normalized property occurrences for the paper observation export."""
    for item in bundle["items"]:
        if item["item_kind"] != "source_record":
            continue
        record = json.loads(item["record_json"])
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
            "items": [item],
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
        routes = bundle["routes"]
        outcomes_by_route = {
            item["route_id"]: item["outcome"]
            for item in _bundle_items(bundle, "source_outcome")
        }
        for item in _bundle_items(bundle, "source_record"):
            identity = SourceRecordItem.model_validate(wire(item)).identity
            record = json.loads(item["record_json"])
            matching_routes = [
                route
                for route in routes
                if identity.source == route["qualified_source"]
                or identity.source in route.get("output_sources", [])
            ]
            if len(matching_routes) != 1:
                raise ValueError(
                    f"{identity.source}:{identity.source_id}: exact execution route is ambiguous"
                )
            route = matching_routes[0]
            outcome = outcomes_by_route.get(route["route_id"])
            if outcome is None:
                raise ValueError(
                    f"{identity.source}: contributing source has no outcome"
                )
            contribution = contributions.setdefault(
                identity.source,
                {
                    "source": identity.source,
                    "provider": identity.provider,
                    "execution_route": route["qualified_source"],
                    "route_status": outcome["status"],
                    "record_completeness": outcome["record_completeness"],
                    "record_count_in_rq2_shard": 0,
                    "data_categories": set(),
                    "property_names": set(),
                    "representative_record": _representative_record(item, record),
                },
            )
            contribution["record_count_in_rq2_shard"] += 1
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
        thermochemical_context = json.loads(entry_set["entry_set_json"])[
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
    rq2_bundles = _rq2_source_record_bundles(result)
    contributions = _source_contribution_map(rq2_bundles)
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
                        "route_status": contribution["route_status"],
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
        "rq2_source_record_exhaustion_shard_bundle_ids": [
            bundle["bundle_id"] for bundle in rq2_bundles
        ],
        "declared_source_scope": {
            "catalog_and_configuration": "MatRouter v0.9.2 capability catalog under the captured runtime configuration",
            **spec["stage_1"],
            "scope_limit": "All capability-matched execution routes were attempted within the declared budgets; this is not every real-world database or every upstream record.",
        },
        "route_outcome_summary": {
            "qualified": aggregate["qualified_route_count"],
            "ready": aggregate["ready_route_count"],
            "attempted": aggregate["attempted_route_count"],
            "status_counts": aggregate["status_counts"],
            "record_completeness_counts": aggregate["record_completeness_counts"],
            "outcomes": [
                {
                    "source": outcome["source"],
                    "status": outcome["status"],
                    "record_count": outcome["record_count"],
                    "reason_code": outcome["reason_code"],
                    "completeness": (outcome.get("record_completeness") or {}).get(
                        "state"
                    ),
                    "truncation_reason": (outcome.get("record_completeness") or {}).get(
                        "truncation_reason"
                    ),
                }
                for outcome in aggregate["source_outcomes"]
            ],
        },
        "rq2_source_record_exhaustion": result["rq2_source_record_exhaustion"],
        "rq2_interpretation_boundary": {
            "observed_landscape_supported": not unsupported_claim_gaps,
            "complete_inventory_eligible": result["rq2_source_record_exhaustion"][
                "complete_inventory_eligible"
            ],
            "semantics": "Shard records may support an observed source-qualified landscape even when a shard is failed, unknown, partial, or truncated. Complete-inventory wording is allowed only when every ready route is sharded and every shard is complete or verified empty.",
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
                    "entry_count": item["entry_count"],
                }
                for item in _case_items(result, "thermochemical_entry_set")
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
    for rq2_bundle in _rq2_source_record_bundles(result):
        for occurrence in _property_occurrences(rq2_bundle):
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
                    "provenance_json": canonical_json(
                        observation.get("provenance") or {}
                    ),
                    "limitations_json": canonical_json(
                        observation.get("limitations") or []
                    ),
                    "record_item_id": item["item_id"],
                }
            )
    for bundle in [primary, *_target_bundles(result)]:
        for item in bundle["items"]:
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
                        "payload_type": item["payload_type"],
                        "content_sha256": sha256_bytes(content.encode()),
                        "pbc_json": canonical_json(parsed_content.get("pbc"))
                        if isinstance(parsed_content, dict)
                        else "null",
                        "limitations_json": canonical_json(
                            item.get("limitations") or []
                        ),
                    }
                )
            elif item["item_kind"] == "scientific_artifact":
                identity = item["identity"]
                descriptor = json.loads(item["descriptor_json"])
                artifacts.append(
                    {
                        "case_name": case_name,
                        "source": identity["source"],
                        "source_id": identity["source_id"],
                        "artifact_item_id": item["item_id"],
                        "artifact_type": item["artifact_type"],
                        "payload_type": item["payload_type"],
                        "payload_sha256": descriptor.get("payload_sha256"),
                        "descriptor_json": canonical_json(descriptor),
                        "limitations_json": canonical_json(
                            item.get("limitations") or []
                        ),
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
    outcomes = {
        item["outcome"]["source"]: item["outcome"]
        for item in _bundle_items(bundle, "source_outcome")
        if item["outcome"]["operation"] == "search_materials"
    }
    rows: list[dict[str, Any]] = []
    for route in sorted(bundle["routes"], key=lambda row: row["qualified_source"]):
        outcome = outcomes.get(route["qualified_source"])
        completeness = (outcome or {}).get("record_completeness") or {}
        rows.append(
            {
                "case_name": case_name,
                "source": route["qualified_source"],
                "output_sources_json": canonical_json(route.get("output_sources", [])),
                "qualified": True,
                "route_state": route["state"],
                "executed": outcome is not None,
                "status": outcome["status"] if outcome is not None else "not_executed",
                "succeeded": outcome is not None and outcome["status"] == "succeeded",
                "verified_empty": outcome is not None
                and outcome["status"] == "empty"
                and completeness.get("state") == "empty",
                "partial": outcome is not None and outcome["status"] == "partial",
                "failed": outcome is not None and outcome["status"] == "failed",
                "record_count": outcome["record_count"] if outcome is not None else 0,
                "completeness": completeness.get("state", "not_executed"),
                "upstream_total": completeness.get("upstream_total"),
                "pages_fetched": completeness.get("pages_fetched", 0),
                "truncation_reason": completeness.get("truncation_reason"),
                "reason_code": outcome["reason_code"]
                if outcome is not None
                else "route_not_ready",
            }
        )
    return rows


def _source_outcome_audit_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = _primary_aggregate_bundle(result)
    outcomes = {
        item["outcome"]["source"]: item["outcome"]
        for item in _bundle_items(bundle, "source_outcome")
        if item["outcome"]["operation"] == "search_materials"
    }
    record_sources = [
        json.loads(item["record_json"])["source"]
        for item in _bundle_items(bundle, "source_record")
    ]

    def optional_value(value: object) -> object:
        if isinstance(value, dict) and "present" in value:
            return value.get("value") if value["present"] else None
        return value

    rows: list[dict[str, Any]] = []
    for route in sorted(bundle["routes"], key=lambda row: row["qualified_source"]):
        qualified_source = route["qualified_source"]
        outcome = outcomes[qualified_source]
        output_sources = set(route.get("output_sources", []))
        actual_sources = [
            source
            for source in record_sources
            if source == qualified_source or source in output_sources
        ]
        actual_count = len(actual_sources)
        completeness = outcome["record_completeness"]
        returned_count = completeness["returned_count"]
        rows.append(
            {
                "case_name": result["case_name"],
                "qualified_source_route": qualified_source,
                "output_sources_json": canonical_json(route.get("output_sources", [])),
                "route_state": route["state"],
                "status": outcome["status"],
                "reason_code": outcome["reason_code"],
                "record_count": outcome["record_count"],
                "returned_count": returned_count,
                "actual_bundle_record_count": actual_count,
                "actual_bundle_record_sources_json": canonical_json(
                    sorted(Counter(actual_sources).items())
                ),
                "record_count_matches_actual": outcome["record_count"] == actual_count,
                "returned_count_matches_actual": returned_count == actual_count,
                "record_completeness_state": completeness["state"],
                "upstream_total": completeness.get("upstream_total"),
                "pages_fetched": completeness["pages_fetched"],
                "last_cursor": completeness.get("last_cursor"),
                "exhaustion_evidence": completeness.get("exhaustion_evidence"),
                "truncation_reason": completeness.get("truncation_reason"),
                "failure_type": optional_value(outcome.get("failure_type")),
                "message": optional_value(outcome.get("message")),
                "extensions_json": canonical_json(outcome.get("extensions", [])),
            }
        )
    return rows


def _rq2_source_outcome_audit_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for capsule in result["evidence_bundles"]:
        if capsule["bundle_role"] != "source_record_exhaustion_shard":
            continue
        bundle = capsule["evidence_bundle"]
        route = bundle["routes"][0]
        outcome_items = _bundle_items(bundle, "source_outcome")
        if len(bundle["routes"]) != 1 or len(outcome_items) != 1:
            raise ValueError("RQ2 source-record shard must have one route and outcome")
        outcome = outcome_items[0]["outcome"]
        qualified_source = capsule["qualified_source_route"]
        output_sources = set(route.get("output_sources", []))
        record_sources = [
            json.loads(item["record_json"])["source"]
            for item in _bundle_items(bundle, "source_record")
        ]
        actual_sources = [
            source
            for source in record_sources
            if source == qualified_source or source in output_sources
        ]
        completeness = outcome["record_completeness"]
        rows.append(
            {
                "case_name": result["case_name"],
                "shard_bundle_id": bundle["bundle_id"],
                "qualified_source_route": qualified_source,
                "output_sources_json": canonical_json(route.get("output_sources", [])),
                "status": outcome["status"],
                "reason_code": outcome["reason_code"],
                "record_count": outcome["record_count"],
                "returned_count": completeness["returned_count"],
                "actual_bundle_record_count": len(actual_sources),
                "actual_bundle_record_sources_json": canonical_json(
                    sorted(Counter(actual_sources).items())
                ),
                "record_count_matches_actual": outcome["record_count"]
                == len(actual_sources),
                "returned_count_matches_actual": completeness["returned_count"]
                == len(actual_sources),
                "record_completeness_state": completeness["state"],
                "upstream_total": completeness.get("upstream_total"),
                "pages_fetched": completeness["pages_fetched"],
                "last_cursor": completeness.get("last_cursor"),
                "exhaustion_evidence": completeness.get("exhaustion_evidence"),
                "truncation_reason": completeness.get("truncation_reason"),
            }
        )
    return rows


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
    from matrouter.evidence_contracts import ThermochemicalEntrySetItem
    from matrouter.phase_diagram import (
        PhaseDiagramDataset,
        PhaseDiagramMethodParameters,
        PhaseDiagramPlotParameters,
        PhaseDiagramRequest,
        compute_phase_diagrams,
    )

    bundle = bundle_model.model_dump(mode="json", exclude_computed_fields=True)
    thermo_outcomes = [
        item["outcome"]
        for item in bundle["items"]
        if item["item_kind"] == "source_outcome"
        and item["outcome"]["operation"] == "get_thermochemical_entries"
    ]
    if len(thermo_outcomes) != 1:
        return None
    outcome = thermo_outcomes[0]
    completeness = outcome.get("record_completeness") or {}
    if outcome["status"] != "succeeded" or completeness.get("state") != "complete":
        return None
    entry_sets = [
        item
        for item in bundle_model.items
        if isinstance(item, ThermochemicalEntrySetItem)
    ]
    if len(entry_sets) != 1:
        return None
    entry_set = entry_sets[0]
    if entry_set.identity.source != "materials_project" or entry_set.entry_count < 2:
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
        matches = [
            (
                capsule["evidence_bundle"]["bundle_id"],
                StructureItem.model_validate(wire(item)),
            )
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "target_followup"
            for item in capsule["evidence_bundle"]["items"]
            if item["item_kind"] == "structure"
            and item["identity"]["source"] == target["qualified_source_route"]
            and item["identity"]["source_id"] == target["source_id"]
        ]
        if len(matches) != 1:
            return None
        selected.append(matches[0])
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
    for item in bundle_model.items:
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
    entry_sets = _case_items(result, "thermochemical_entry_set")
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
            "aggregate_status_counts": aggregate["status_counts"],
            "aggregate_completeness_counts": aggregate["record_completeness_counts"],
            "rq2_source_record_exhaustion": result["rq2_source_record_exhaustion"],
            "exact_target_audit": result["protocol_conformance"][
                "stage_2_target_audit"
            ],
            "exact_target_artifacts": scientific_rows["artifacts"],
            "explicit_method_names": [row["method_name"] for row in methods],
            "thermochemical_entry_count": sum(
                item["entry_count"] for item in entry_sets
            ),
            "explicitly_identified_experimental_band_gap_observation_count": len(
                explicitly_experimental_band_gaps
            ),
            "qualified_source_route_count_semantics": QUALIFIED_ROUTE_COUNT_SEMANTICS,
        },
        "stage_1_scope": STAGE_1_SCOPE,
        "rq2_shard_scope": RQ2_SHARD_SCOPE,
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
    entry_set_payload = json.loads(entry_set["entry_set_json"])
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
        descriptor = json.loads(item["descriptor_json"])
        structure_identity = descriptor["source_native_structure_identity"]
        rows.append(
            {
                "case_name": result["case_name"],
                "source": item["identity"]["source"],
                "source_id": item["identity"]["source_id"],
                "formula": descriptor["formula"],
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
                "payload_sha256": descriptor["payload_sha256"],
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
                sorted(requirement.requirement_id for requirement in requirements)
            ),
            acquisition_ids=tuple(
                sorted(acquisition.acquisition_id for acquisition in acquisitions)
            ),
        )
    )


def _rq2_source_record_summary(
    bundle_capsules: list[dict[str, Any]], primary_bundle: dict[str, Any]
) -> dict[str, Any]:
    from matrouter.evidence_contracts import SourceRecordItem

    ready_routes = [
        route["qualified_source"]
        for route in sorted(
            primary_bundle["routes"], key=lambda row: row["qualified_source"]
        )
        if route["state"] == "ready" and route["operation"] == "search_materials"
    ]
    shards = [
        capsule
        for capsule in bundle_capsules
        if capsule["bundle_role"] == "source_record_exhaustion_shard"
    ]
    shard_routes = [capsule["qualified_source_route"] for capsule in shards]
    outcomes: list[dict[str, Any]] = []
    record_identities = []
    for capsule in shards:
        bundle = capsule["evidence_bundle"]
        outcome_items = _bundle_items(bundle, "source_outcome")
        if len(outcome_items) != 1:
            raise ValueError("RQ2 source-record shard must have exactly one outcome")
        outcome = outcome_items[0]["outcome"]
        if outcome["source"] != capsule["qualified_source_route"]:
            raise ValueError("RQ2 source-record shard outcome route mismatch")
        outcomes.append(outcome)
        record_identities.extend(
            SourceRecordItem.model_validate(wire(item)).identity
            for item in _bundle_items(bundle, "source_record")
        )
    gaps = []
    for outcome in outcomes:
        completeness = outcome.get("record_completeness") or {}
        if (outcome["status"], completeness.get("state")) in {
            ("succeeded", "complete"),
            ("empty", "empty"),
        }:
            continue
        gaps.append(
            {
                "source": outcome["source"],
                "status": outcome["status"],
                "record_completeness": completeness.get("state"),
                "record_count": outcome["record_count"],
                "upstream_total": completeness.get("upstream_total"),
                "reason_code": outcome["reason_code"],
                "truncation_reason": completeness.get("truncation_reason"),
            }
        )
    all_ready_routes_sharded = shard_routes == ready_routes
    return {
        "semantics": "Every ready primary search route receives one stable-order selected-source exhaust-upstream run. Complete inventory eligibility requires every shard to be complete or verified empty; all other states remain explicit gaps.",
        "ready_route_count": len(ready_routes),
        "shard_count": len(shards),
        "shard_routes": shard_routes,
        "shard_bundle_ids": [
            capsule["evidence_bundle"]["bundle_id"] for capsule in shards
        ],
        "all_ready_routes_sharded": all_ready_routes_sharded,
        "source_record_count": sum(row["record_count"] for row in outcomes),
        "source_record_item_count": sum(
            len(_bundle_items(capsule["evidence_bundle"], "source_record"))
            for capsule in shards
        ),
        "source_record_sources": sorted(
            {identity.source for identity in record_identities}
        ),
        "source_record_providers": sorted(
            {identity.provider for identity in record_identities}
        ),
        "status_counts": dict(
            sorted(Counter(row["status"] for row in outcomes).items())
        ),
        "record_completeness_counts": dict(
            sorted(
                Counter(
                    (row.get("record_completeness") or {}).get("state", "missing")
                    for row in outcomes
                ).items()
            )
        ),
        "complete_inventory_eligible": all_ready_routes_sharded and not gaps,
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def acquire_source_record_layers(
    router: Any,
    *,
    case_name: str,
    formula: str,
) -> dict[str, Any]:
    """Acquire the bounded RQ1 aggregate and non-selective per-route RQ2 shards."""
    from matrouter.tools.evidence import (
        AggregateSourceRecordsRequest,
        BeginEvidenceRunRequest,
        EvidenceTools,
    )
    from matrouter.tools.run_state import SessionRunRegistry

    primary_tools = EvidenceTools(router, SessionRunRegistry())
    primary_run = primary_tools.begin_evidence_run(BeginEvidenceRunRequest())
    discovery = _create_requirement(
        primary_tools,
        primary_run.evidence_run_id,
        label=f"{case_name}-all-qualified-source-records",
        subject=_subject(formula=formula),
        kind="source_record",
        use="Acquire the one primary all-qualified cross-source source-record Bundle through MatRouter's logical all-route fan-out.",
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
    raw_runs = [
        {
            "run_role": "primary_aggregate",
            "qualified_source_route": None,
            "run_capacity": primary_run.capacity.model_dump(mode="json"),
            "requirements": [discovery.model_dump(mode="json")],
            "routes": [route.model_dump(mode="json") for route in primary_routes],
            "acquisitions": [],
            "canonical_bundle": primary_bundle,
        }
    ]
    bundle_capsules = [
        {
            "bundle_role": "primary_aggregate",
            "qualified_source_route": None,
            "evidence_bundle": primary_bundle,
        }
    ]

    ready_search_routes = [
        route
        for route in primary_routes
        if route.state == "ready" and route.operation == "search_materials"
    ]
    for route_index, primary_route in enumerate(ready_search_routes):
        shard_tools = EvidenceTools(router, SessionRunRegistry())
        shard_run = shard_tools.begin_evidence_run(BeginEvidenceRunRequest())
        shard_requirement = _create_requirement(
            shard_tools,
            shard_run.evidence_run_id,
            label=(
                f"{case_name}-{_safe_label(primary_route.qualified_source)}-"
                "source-record-exhaustion"
            ),
            subject=_subject(formula=formula),
            kind="source_record",
            use=(
                "Non-selective exact-route RQ2 source-record exhaustion shard; "
                "kept separate from the RQ1 primary aggregate."
            ),
            constraints=_constraints(
                sources=(primary_route.qualified_source,),
                limit=shard_run.capacity.max_single_source_record_items,
            ),
        )
        shard_routes = _route(shard_tools, shard_run.evidence_run_id, shard_requirement)
        selected_routes = [
            route
            for route in shard_routes
            if route.qualified_source == primary_route.qualified_source
            and route.operation == "search_materials"
            and route.state == "ready"
        ]
        if len(selected_routes) != 1:
            raise ValueError(
                f"{case_name}: ready primary route {primary_route.qualified_source} "
                "did not resolve to one ready selected-source shard route"
            )
        acquisition = _execute(
            shard_tools,
            shard_run.evidence_run_id,
            shard_requirement,
            selected_routes[0],
            f"paper-release-{case_name}-rq2-shard-{route_index:02d}",
        )
        shard_bundle_model = _assemble_run(
            shard_tools,
            shard_run.evidence_run_id,
            [shard_requirement],
            [acquisition],
        )
        shard_bundle = shard_bundle_model.model_dump(
            mode="json", exclude_computed_fields=True
        )
        raw_runs.append(
            _serialized_run(
                run_role="source_record_exhaustion_shard",
                qualified_source_route=primary_route.qualified_source,
                run=shard_run,
                requirements=[shard_requirement],
                routes=shard_routes,
                acquisitions=[acquisition],
            )
        )
        bundle_capsules.append(
            {
                "bundle_role": "source_record_exhaustion_shard",
                "qualified_source_route": primary_route.qualified_source,
                "evidence_bundle": shard_bundle,
            }
        )

    rq2_shard_summary = _rq2_source_record_summary(bundle_capsules, primary_bundle)

    return {
        "raw_runs": raw_runs,
        "bundle_capsules": bundle_capsules,
        "primary_bundle_model": primary_bundle_model,
        "primary_routes": primary_routes,
        "qualified_sources": qualified_sources,
        "primary_summary": _aggregate_summary(primary_bundle),
        "rq2_shard_summary": rq2_shard_summary,
    }


def acquire_case(
    case_name: str,
    *,
    raw_output_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    from matrouter import create_router
    from matrouter.evidence_contracts import SourceFilter
    from matrouter.evidence_contracts import canonical_json as matrouter_canonical_json
    from matrouter.tools.evidence import (
        BeginEvidenceRunRequest,
        CapabilityRequest,
        EvidenceTools,
    )
    from matrouter.tools.run_state import SessionRunRegistry

    spec = case_spec(case_name)
    case_started = time.monotonic()
    formula = spec["formula"]
    router = create_router()
    try:
        capability_tools = EvidenceTools(router, SessionRunRegistry())
        capability = capability_tools.inspect_evidence_capabilities(CapabilityRequest())
        capability_audit = _capability_audit(capability)
        source_record_layers = acquire_source_record_layers(
            router,
            case_name=case_name,
            formula=formula,
        )
        aggregate_bundle_model = source_record_layers["primary_bundle_model"]
        qualified_sources = source_record_layers["qualified_sources"]
        aggregate_bundle = aggregate_bundle_model.model_dump(
            mode="json", exclude_computed_fields=True
        )
        raw_runs = source_record_layers["raw_runs"]
        bundle_capsules: list[dict[str, Any]] = source_record_layers["bundle_capsules"]
        rq2_shard_summary = source_record_layers["rq2_shard_summary"]
        coverage = _aggregate_coverage_rows(case_name, aggregate_bundle)
        methods: list[dict[str, Any]] = []
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
            target_tools = EvidenceTools(router, SessionRunRegistry())
            target_run = target_tools.begin_evidence_run(BeginEvidenceRunRequest())
            target_run_id = target_run.evidence_run_id
            requirements: list[Any] = []
            routes: list[Any] = []
            acquisitions: list[Any] = []
            target_discovery = _create_requirement(
                target_tools,
                target_run_id,
                label=f"{case_name}-{_safe_label(source)}-exact-target-prerequisite",
                subject=_subject(formula=formula),
                kind="source_record",
                use="Resolve only preregistered exact target identities required for declared follow-up artifacts; this is not a route-coverage run.",
                constraints=_constraints(
                    sources=(source,),
                    limit=SOURCE_RECORD_SAFETY_LIMIT,
                ),
            )
            requirements.append(target_discovery)
            target_routes = _route(target_tools, target_run_id, target_discovery)
            routes.extend(target_routes)
            discovery_acquisitions: list[Any] = []
            for route_index, target_route in enumerate(
                sorted(target_routes, key=lambda row: row.route_id)
            ):
                if target_route.state != "ready":
                    continue
                acquisition = _execute(
                    target_tools,
                    target_run_id,
                    target_discovery,
                    target_route,
                    f"paper-release-{case_name}-target-{source_index:02d}-{route_index:02d}",
                )
                discovery_acquisitions.append(acquisition)
                acquisitions.append(acquisition)
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
                        tools=target_tools,
                        run_id=target_run_id,
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
            target_bundle_model = _assemble_run(
                target_tools, target_run_id, requirements, acquisitions
            )
            target_bundle = target_bundle_model.model_dump(
                mode="json", exclude_computed_fields=True
            )
            raw_runs.append(
                _serialized_run(
                    run_role="target_followup",
                    qualified_source_route=source,
                    run=target_run,
                    requirements=requirements,
                    routes=routes,
                    acquisitions=acquisitions,
                )
            )
            bundle_capsules.append(
                {
                    "bundle_role": "target_followup",
                    "qualified_source_route": source,
                    "evidence_bundle": target_bundle,
                }
            )
            if case_name == "mos2-band-gap" and source == "materials_project":
                methods.extend(_render_spectral_methods(case_name, target_bundle_model))

        if case_name == "mos2-band-gap":
            structure_match = _match_preregistered_mos2_structures(
                bundle_capsules, spec
            )
            if structure_match is not None:
                methods.append(structure_match)

        if case_name == "lifepo4-stability":
            thermo_tools = EvidenceTools(router, SessionRunRegistry())
            thermo_run = thermo_tools.begin_evidence_run(BeginEvidenceRunRequest())
            thermo_run_id = thermo_run.evidence_run_id
            source_filter = SourceFilter(
                source="materials_project",
                filter_json=matrouter_canonical_json({"thermo_types": [THERMO_TYPE]}),
            )
            thermo = _create_requirement(
                thermo_tools,
                thermo_run_id,
                label="lifepo4-materials-project-frame-compatible-entries",
                subject=_subject(elements=("Fe", "Li", "O", "P")),
                kind="thermochemical_entries",
                use="Exact source-compatible Li-Fe-O-P entry set for one explicit phase-diagram panel.",
                constraints=_constraints(
                    sources=("materials_project",),
                    limit=THERMOCHEMICAL_LIMIT,
                    filters=(source_filter,),
                ),
            )
            thermo_requirements = [thermo]
            thermo_routes = _route(thermo_tools, thermo_run_id, thermo)
            thermo_acquisitions: list[Any] = []
            for route in thermo_routes:
                if (
                    route.state == "ready"
                    and route.operation == "get_thermochemical_entries"
                ):
                    thermo_acquisitions.append(
                        _execute(
                            thermo_tools,
                            thermo_run_id,
                            thermo,
                            route,
                            "paper-release-lifepo4-thermochemical-entries",
                        )
                    )
            thermo_bundle_model = _assemble_run(
                thermo_tools,
                thermo_run_id,
                thermo_requirements,
                thermo_acquisitions,
            )
            thermo_bundle = thermo_bundle_model.model_dump(
                mode="json", exclude_computed_fields=True
            )
            raw_runs.append(
                _serialized_run(
                    run_role="thermochemical",
                    qualified_source_route="materials_project",
                    run=thermo_run,
                    requirements=thermo_requirements,
                    routes=thermo_routes,
                    acquisitions=thermo_acquisitions,
                )
            )
            bundle_capsules.append(
                {
                    "bundle_role": "thermochemical",
                    "qualified_source_route": "materials_project",
                    "evidence_bundle": thermo_bundle,
                }
            )
            phase_result = _compute_lifepo4_phase_diagram(thermo_bundle_model)
            if phase_result is not None:
                methods.append(_portable_method_result(phase_result))
    finally:
        router.close()

    case_elapsed_seconds = round(time.monotonic() - case_started, 3)
    raw_capture = {
        "schema_version": "matrouter.paper-live-capture/6",
        "case_name": case_name,
        "protocol_version": PROTOCOL_VERSION,
        "release_binding": load_json(IDENTITY_PATH),
        "retrieval_strategy": {
            "stage_1": spec["stage_1"],
            "primary_aggregate": STAGE_1_SCOPE,
            "rq2_source_record_exhaustion_shards": spec[
                "rq2_source_record_exhaustion_shards"
            ],
            "rq2_shard_scope": RQ2_SHARD_SCOPE,
            "stage_2_targets": spec["stage_2_targets"],
            "stage_2_selection_rule": "only exact targets preregistered before the live run; target prerequisite searches and artifact acquisitions are follow-up Bundles, not route-coverage runs, and no target is dynamically replaced",
            "qualified_source_routes": qualified_sources,
        },
        "qualified_source_routes": qualified_sources,
        "capability_audit": capability_audit,
        "capability_snapshot": capability.model_dump(mode="json"),
        "rq2_source_record_exhaustion": rq2_shard_summary,
        "runs": raw_runs,
        "case_elapsed_seconds": case_elapsed_seconds,
    }
    if raw_output_path is not None:
        write_json(raw_output_path, raw_capture)
    _, protocol_conformance = _capture_protocol_status(raw_capture, spec)
    result = {
        "schema_version": "matrouter.paper-case-result/12",
        "case_name": case_name,
        "protocol_version": PROTOCOL_VERSION,
        "research_questions": COMMON_RESEARCH_QUESTIONS,
        "rq2_source_record_exhaustion_shard_policy": RQ2_SHARD_POLICY,
        "rq3_method_applicability": spec["rq3_method_applicability"],
        "scientific_question": spec["scientific_question"],
        "task_spec": spec,
        "actual_retrieval_strategy": raw_capture["retrieval_strategy"],
        "protocol_conformance": protocol_conformance,
        "coverage_matrix": coverage,
        "evidence_bundles": bundle_capsules,
        "primary_result_bundle_id": aggregate_bundle["bundle_id"],
        "aggregate": _aggregate_summary(aggregate_bundle),
        "rq2_source_record_exhaustion": rq2_shard_summary,
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
    rq2_source_outcome_audit = [
        row for result in results for row in _rq2_source_outcome_audit_rows(result)
    ]
    with (RESULTS / "rq2-source-outcome-audit.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rq2_source_outcome_audit[0]))
        writer.writeheader()
        writer.writerows(rq2_source_outcome_audit)
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
        rq2_summary = result["rq2_source_record_exhaustion"]
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
            "aggregate_status_counts_json": canonical_json(aggregate["status_counts"]),
            "aggregate_completeness_counts_json": canonical_json(
                aggregate["record_completeness_counts"]
            ),
            "aggregate_capacity_limitation_count": len(
                aggregate["capacity_limitations"]
            ),
            "rq2_shard_count": rq2_summary["shard_count"],
            "rq2_source_record_count": rq2_summary["source_record_count"],
            "rq2_status_counts_json": canonical_json(rq2_summary["status_counts"]),
            "rq2_completeness_counts_json": canonical_json(
                rq2_summary["record_completeness_counts"]
            ),
            "rq2_gap_count": rq2_summary["gap_count"],
            "rq2_gaps_json": canonical_json(rq2_summary["gaps"]),
            "rq2_complete_inventory_eligible": rq2_summary[
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
                item["entry_count"]
                for item in _case_items(result, "thermochemical_entry_set")
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
                    "status_counts": aggregate["status_counts"],
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
                "rq2_source_record_exhaustion": {
                    key: value
                    for key, value in rq2_summary.items()
                    if key not in {"shard_bundle_ids", "shard_routes"}
                },
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


def _validate_rq2_source_outcome_export_consistency(
    results_by_case: dict[str, dict[str, Any]],
) -> None:
    with (RESULTS / "rq2-source-outcome-audit.csv").open(newline="") as handle:
        actual = list(csv.DictReader(handle))
    expected_rows = [
        row
        for case_name in CASES
        for row in _rq2_source_outcome_audit_rows(results_by_case[case_name])
    ]
    expected = [
        {key: "" if value is None else str(value) for key, value in row.items()}
        for row in expected_rows
    ]
    if actual != expected:
        raise ValueError("rq2-source-outcome-audit.csv export drift")


def _diagnose_stage1_product_blockers(
    case_name: str, outcomes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Classify only source-independent contract/request failures as product blockers."""
    blockers: list[dict[str, Any]] = []
    for outcome in outcomes:
        reason_code = outcome.get("reason_code")
        message_field = outcome.get("message")
        message = (
            message_field.get("value")
            if isinstance(message_field, dict) and message_field.get("present")
            else message_field
            if isinstance(message_field, str)
            else None
        )
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
            "source": outcome.get("source"),
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
    outcomes = [
        item["outcome"]
        for capsule in result["evidence_bundles"]
        if capsule["bundle_role"] == "primary_aggregate"
        for item in capsule["evidence_bundle"]["items"]
        if item["item_kind"] == "source_outcome"
        and item["outcome"]["operation"] == "search_materials"
    ]
    return _diagnose_stage1_product_blockers(result["case_name"], outcomes)


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
            outcome for outcome in outcomes if outcome["status"] == "failed"
        ]
        raw_path = RAW / identity["package_version"] / "lifepo4-stability.json"
        if failed_outcomes and raw_path.is_file():
            raw = load_json(raw_path)
            failed_acquisitions = [
                acquisition
                for run in raw["runs"]
                for acquisition in run["acquisitions"]
                if acquisition["route"]["operation"] == "get_thermochemical_entries"
                and acquisition["outcome_draft"]["status"] == "failed"
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
                        "schema_version": "matrouter.paper-typed-reproduction/1",
                        "release_binding": {
                            "package": f"matrouter=={identity['package_version']}",
                            "tag": identity["release_tag"],
                            "commit": identity["product_commit"],
                        },
                        "reproduction_kind": "stored_exact_typed_acquisition_slice",
                        "raw_capture": str(raw_path.relative_to(ROOT)),
                        "requirement": acquisition["requirement"],
                        "route": acquisition["route"],
                        "outcome_draft": acquisition["outcome_draft"],
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
                "configured_entry_limit": THERMOCHEMICAL_LIMIT,
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
            "schema_version": "matrouter.paper-product-blockers/1",
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
        descriptor = json.loads(item["descriptor_json"])
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
        bundle["bundle_id"]: {item["item_id"] for item in bundle["items"]}
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
        and item.get("payload_content")
        and item.get("payload_integrity_status") == "verified"
        and item.get("payload_type")
        and item.get("identity", {}).get("source")
        and item.get("identity", {}).get("source_id")
    }


def _successful_spectral_render_input_ids(result: dict[str, Any]) -> set[str]:
    complete_artifacts = _complete_spectral_artifact_ids(result)
    items_by_bundle = {
        bundle["bundle_id"]: {item["item_id"] for item in bundle["items"]}
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
        and item.get("payload_content")
        and item.get("payload_integrity_status") == "verified"
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
        item["outcome"]
        for item in _case_items(result, "source_outcome")
        if item["outcome"]["operation"] == "get_thermochemical_entries"
    ]


def _complete_thermochemical_entry_sets(
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    complete_outcomes = [
        outcome
        for outcome in _thermochemical_outcomes(result)
        if outcome["status"] == "succeeded"
        and outcome.get("record_completeness", {}).get("state") == "complete"
    ]
    entry_sets = [
        item
        for item in _case_items(result, "thermochemical_entry_set")
        if item.get("entry_set_json")
        and item.get("entry_count", 0) >= 2
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
            for item in capsule["evidence_bundle"]["items"]
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
        and len(entries) == entry_set["entry_count"]
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
            outcome["status"] != "succeeded"
            or outcome.get("record_completeness", {}).get("state") != "complete"
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
        "schema_version": "matrouter.paper-internal-protocol-review/6",
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
            "rq2_shards_cover_every_ready_primary_search_route_in_stable_order": all(
                result["case_interpretation"]["rq2_shard_scope"] == RQ2_SHARD_SCOPE
                and result["protocol_conformance"][
                    "rq2_source_record_exhaustion_shards"
                ]["passed"]
                and result["rq2_source_record_exhaustion"]["all_ready_routes_sharded"]
                for result in results
            ),
            "rq2_incomplete_shards_never_claim_complete_inventory": all(
                result["rq2_source_record_exhaustion"]["complete_inventory_eligible"]
                == (result["rq2_source_record_exhaustion"]["gap_count"] == 0)
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
            "only_declared_run_roles_and_nonselective_rq2_shards": all(
                all(
                    run["run_role"]
                    in {
                        "primary_aggregate",
                        "source_record_exhaustion_shard",
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
                    and result["protocol_conformance"][
                        "rq2_source_record_exhaustion_shards"
                    ]["passed"]
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
                    "rq2-source-outcome-audit.csv",
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
        RESULTS / "rq2-source-outcome-audit.csv",
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
                label=f"{case_name}-preflight",
                subject=_subject(formula=spec["formula"]),
                kind="source_record",
                use="Non-executing all-qualified exhaust-upstream preflight.",
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
                or not materials_galaxy_routes[0].output_sources
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
                    "output_sources": list(route.output_sources),
                    "state": route.state,
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
        raise RuntimeError(
            f"final v0.9.2 release-bound run is pending; expected {expected}"
        )


def _planned_raw_paths(identity: dict[str, Any]) -> dict[str, Path]:
    return {
        case_name: RAW / identity["package_version"] / f"{case_name}.json"
        for case_name in CASES
    }


def run_all() -> None:
    live_run_started = time.monotonic()
    identity = verify_release_identity()
    _assert_final_release_binding(identity)
    planned_raw_paths = _planned_raw_paths(identity)
    existing_raw_paths = [path for path in planned_raw_paths.values() if path.exists()]
    if existing_raw_paths:
        raise FileExistsError(
            "planned final raw capture already exists; no active outputs were cleared: "
            + ", ".join(str(path) for path in existing_raw_paths)
        )
    preflight_result = preflight()
    if preflight_result["release_identity"] != identity:
        raise ValueError("preflight release identity drift")
    _clear_active_results()
    results: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    raw_paths: dict[str, Path] = {}
    for case_name in CASES:
        print(f"[{case_name}] starting", flush=True)
        raw_path = planned_raw_paths[case_name]
        _raw, result, case_coverage = acquire_case(case_name, raw_output_path=raw_path)
        result_path = CASE_RESULTS / f"{case_name}.json"
        raw_paths[case_name] = raw_path
        write_json(result_path, result)
        results.append(result)
        coverage.extend(case_coverage)
        entries.append(
            {
                "case_name": case_name,
                "raw_path": str(raw_path.relative_to(ROOT)),
                "raw_sha256": file_sha256(raw_path),
                "result_path": str(result_path.relative_to(ROOT)),
                "result_sha256": file_sha256(result_path),
                "bundle_ids": [bundle["bundle_id"] for bundle in _case_bundles(result)],
                "rq2_source_record_exhaustion": result["rq2_source_record_exhaustion"],
                "case_spec_sha256": file_sha256(ROOT / "cases" / f"{case_name}.json"),
                "paper_result_status": result["paper_result_status"],
            }
        )
        print(
            f"[{case_name}] captured in {result['case_elapsed_seconds']:.3f}s",
            flush=True,
        )
    export_results(results, coverage)
    write_product_blockers(results)
    write_internal_protocol_review(results, raw_paths)
    paper_results_eligible = all(
        result["protocol_conformance"]["capture_eligible_under_frozen_protocol"]
        for result in results
    ) and all(result["paper_results_eligible"] for result in results)
    manifest = {
        "schema_version": "matrouter.paper-manifest/14",
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
        "rq2_source_record_exhaustion_shard_policy": RQ2_SHARD_POLICY,
        "rq3_method_applicability": {
            result["case_name"]: result["rq3_method_applicability"]
            for result in results
        },
        "core_boundary": "MatRouter routes source-qualified evidence and exact method inputs; the Agent builds the case-specific material landscape and scientific handoff.",
        "reference_assessments_enabled": False,
        "release_identity": identity,
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
        "source_record_exhaustion_shard": "source_record_exhaustion_shard",
        "target_followup": "target_followup",
        "thermochemical": "thermochemical",
    }
    for run in raw["runs"]:
        if run["run_role"] == "primary_aggregate":
            bundle = EvidenceBundle.model_validate(wire(run["canonical_bundle"]))
            capsules.append(
                {
                    "bundle_role": "primary_aggregate",
                    "qualified_source_route": None,
                    "evidence_bundle": bundle.model_dump(
                        mode="json", exclude_computed_fields=True
                    ),
                }
            )
            continue
        requirements = tuple(
            EvidenceRequirement.model_validate(wire(row)) for row in run["requirements"]
        )
        routes = tuple(
            RouteCandidate.model_validate(wire(row)) for row in run["routes"]
        )
        acquisitions = tuple(
            EvidenceAcquisitionResult.model_validate(wire(row))
            for row in run["acquisitions"]
        )
        bundle = assemble_acquired_evidence_bundle(
            AcquisitionBundleAssemblyRequest(
                requirements=requirements, routes=routes, acquisitions=acquisitions
            )
        )
        capsules.append(
            {
                "bundle_role": role_names[run["run_role"]],
                "qualified_source_route": run["qualified_source_route"],
                "evidence_bundle": bundle.model_dump(
                    mode="json", exclude_computed_fields=True
                ),
            }
        )
    return capsules


def refresh_derived_outputs() -> None:
    from matrouter.evidence_contracts import EvidenceBundle

    manifest = load_json(RESULTS / "manifest.json")
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
        methods = [
            _portable_method_result(method) for method in result["explicit_methods"]
        ]
        actual_strategy, protocol_conformance = _capture_protocol_status(raw, spec)
        result["schema_version"] = "matrouter.paper-case-result/12"
        result["protocol_version"] = PROTOCOL_VERSION
        result["research_questions"] = COMMON_RESEARCH_QUESTIONS
        result["rq2_source_record_exhaustion_shard_policy"] = RQ2_SHARD_POLICY
        result["rq3_method_applicability"] = spec["rq3_method_applicability"]
        result["scientific_question"] = spec["scientific_question"]
        result["task_spec"] = spec
        result["actual_retrieval_strategy"] = actual_strategy
        result["protocol_conformance"] = protocol_conformance
        result["evidence_bundles"] = bundle_capsules
        aggregate_bundles = [
            capsule["evidence_bundle"]
            for capsule in bundle_capsules
            if capsule["bundle_role"] == "primary_aggregate"
        ]
        if len(aggregate_bundles) != 1:
            raise ValueError(f"{case_name}: expected one primary aggregate Bundle")
        result["primary_result_bundle_id"] = aggregate_bundles[0]["bundle_id"]
        result["aggregate"] = _aggregate_summary(aggregate_bundles[0])
        result["rq2_source_record_exhaustion"] = _rq2_source_record_summary(
            bundle_capsules, aggregate_bundles[0]
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
    manifest["schema_version"] = "matrouter.paper-manifest/14"
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
    manifest["rq2_source_record_exhaustion_shard_policy"] = RQ2_SHARD_POLICY
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
        entry["rq2_source_record_exhaustion"] = result["rq2_source_record_exhaustion"]
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

    if not (RESULTS / "manifest.json").is_file():
        raise FileNotFoundError(
            "current-protocol result manifest has not been generated; final release-bound run is pending"
        )
    identity = verify_release_identity()
    current_specs = {case_name: case_spec(case_name) for case_name in CASES}
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
    if manifest.get("schema_version") != "matrouter.paper-manifest/14":
        raise ValueError(
            "manifest schema mismatch; the forward protocol requires a fresh full "
            "release-bound acquisition and must not refresh frozen legacy results"
        )
    if manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("manifest protocol identity mismatch")
    if manifest.get("research_questions") != COMMON_RESEARCH_QUESTIONS:
        raise ValueError("manifest research-question mismatch")
    if manifest.get("rq2_source_record_exhaustion_shard_policy") != RQ2_SHARD_POLICY:
        raise ValueError("manifest RQ2 exhaustion-shard policy mismatch")
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
        if result.get("schema_version") != "matrouter.paper-case-result/12":
            raise ValueError(f"{entry['case_name']}: result schema mismatch")
        if result.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(f"{entry['case_name']}: result protocol mismatch")
        if raw.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(f"{entry['case_name']}: raw protocol mismatch")
        if raw.get("schema_version") != "matrouter.paper-live-capture/6":
            raise ValueError(f"{entry['case_name']}: raw capture schema mismatch")
        if any(
            run.get("run_role")
            not in {
                "primary_aggregate",
                "source_record_exhaustion_shard",
                "target_followup",
                "thermochemical",
            }
            for run in raw.get("runs", [])
        ):
            raise ValueError(f"{entry['case_name']}: unsupported run role")
        if result.get("research_questions") != COMMON_RESEARCH_QUESTIONS:
            raise ValueError(f"{entry['case_name']}: research-question mismatch")
        if result.get("rq2_source_record_exhaustion_shard_policy") != RQ2_SHARD_POLICY:
            raise ValueError(f"{entry['case_name']}: RQ2 shard policy mismatch")
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
            "rq2_source_record_exhaustion",
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
        expected_rq2_summary = _rq2_source_record_summary(
            result["evidence_bundles"], aggregate_bundle
        )
        if result["rq2_source_record_exhaustion"] != expected_rq2_summary:
            raise ValueError(f"{entry['case_name']}: RQ2 shard summary drift")
        if raw.get("rq2_source_record_exhaustion") != expected_rq2_summary:
            raise ValueError(f"{entry['case_name']}: raw RQ2 shard summary drift")
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
        if entry.get("rq2_source_record_exhaustion") != expected_rq2_summary:
            raise ValueError(f"{entry['case_name']}: manifest RQ2 summary drift")
        bundle_item_ids = {
            item["item_id"]
            for bundle in _case_bundles(result)
            for item in bundle["items"]
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
    _validate_rq2_source_outcome_export_consistency(results_by_case)
    for export in manifest["exports"]:
        if file_sha256(ROOT / export["path"]) != export["sha256"]:
            raise ValueError(f"export digest drift: {export['path']}")
    forbidden = (str(Path.home()), str(Path("/private/tmp")))
    for path in [ROOT / row["raw_path"] for row in manifest["case_results"]] + [
        ROOT / row["result_path"] for row in manifest["case_results"]
    ]:
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
        for case_name in CASES:
            replay_case(case_name)
    elif args.command == "refresh":
        refresh_derived_outputs()
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
