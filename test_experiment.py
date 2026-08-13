from __future__ import annotations

import importlib.util
import inspect
import unittest
from pathlib import Path
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    "paper_experiment", Path(__file__).with_name("experiment.py")
)
assert SPEC and SPEC.loader
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)
ROOT = Path(__file__).resolve().parent


class EvaluationHarnessTests(unittest.TestCase):
    def test_release_identity_is_exact_pypi_v0102(self) -> None:
        identity = experiment.load_json(ROOT / "product-identity.release.json")
        self.assertEqual(identity["package_version"], "0.10.2")
        self.assertEqual(identity["public_VERSION"], "0.10.2")
        self.assertEqual(identity["release_tag"], "v0.10.2")
        self.assertEqual(
            identity["product_commit"],
            "bb163755f05be59f74b4d2d19875dfd2bc497b4b",
        )
        self.assertEqual(
            identity["wheel_sha256"],
            "21d6e7c40b2a313d728d88fe9becb42ec5b8fa3daafaf5786c7e049337900010",
        )
        self.assertEqual(
            identity["sdist_sha256"],
            "ed24f0ced59e6a118f22d7bb943944ac42842c72f684b1640f7568b56fe0c6c7",
        )
        provenance = identity["pypi_provenance"]
        self.assertEqual(provenance["workflow_run_id"], 31651096283)
        self.assertEqual(provenance["workflow_run_conclusion"], "success")

    def test_runtime_distribution_is_registry_install_without_source_injection(
        self,
    ) -> None:
        audit = experiment._runtime_distribution_audit()
        self.assertEqual(audit["distribution_version"], "0.10.2")
        self.assertEqual(audit["public_VERSION"], "0.10.2")
        self.assertTrue(audit["direct_url_json_absent"])
        self.assertEqual(audit["product_source_pythonpath_entries"], 0)
        self.assertEqual(audit["imported_package_path"], "site-packages/matrouter")
        self.assertEqual(audit["distribution_package_path"], "site-packages/matrouter")

    def test_registry_distribution_guard_rejects_editable_and_source_checkout(
        self,
    ) -> None:
        imported_root = (
            ROOT / ".venv" / "lib" / "python3.12" / "site-packages" / "matrouter"
        )
        installed = Mock()
        installed.locate_file.return_value = imported_root
        installed.read_text.return_value = None
        self.assertTrue(
            experiment._registry_distribution_matches_import(installed, imported_root)
        )
        installed.read_text.return_value = (
            '{"url":"../matrouter","dir_info":{"editable":true}}'
        )
        self.assertFalse(
            experiment._registry_distribution_matches_import(installed, imported_root)
        )
        installed.read_text.return_value = None
        self.assertFalse(
            experiment._registry_distribution_matches_import(
                installed, ROOT.parent / "matrouter" / "matrouter"
            )
        )

    def test_dependency_is_exact_registry_pin(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text()
        lock = (ROOT / "uv.lock").read_text()
        self.assertIn('dependencies = ["matrouter==0.10.2"]', pyproject)
        self.assertIn('name = "matrouter"', lock)
        self.assertIn('version = "0.10.2"', lock)
        self.assertNotIn("../matrouter", pyproject + lock)
        self.assertNotIn("editable = true", pyproject + lock)

    def test_exactly_three_cases_and_one_protocol_identity(self) -> None:
        self.assertEqual(
            experiment.CASES,
            ("mos2-band-gap", "lifepo4-stability", "bi2se3-topology"),
        )
        self.assertEqual(
            experiment.PROTOCOL_VERSION, "matrouter.paper-three-case-protocol"
        )

    def test_common_rq2_is_a_view_of_the_same_bundle(self) -> None:
        self.assertEqual(
            tuple(experiment.COMMON_RESEARCH_QUESTIONS), ("RQ1", "RQ2", "RQ3")
        )
        rq2 = experiment.COMMON_RESEARCH_QUESTIONS["RQ2"]
        self.assertIn("same authoritative aggregate Bundle", rq2)
        self.assertNotIn("per-route source-record", rq2)

    def test_case_specs_use_shared_discovery_policy(self) -> None:
        expected_stage = {
            "evidence_kind": "source_record",
            "source_scope": "all_qualified",
            "record_scope": "exhaust_upstream",
            "engineering_ceiling_authority": "matrouter_product_defaults",
            "evaluation_ceiling_overrides": [],
        }
        for case_name in experiment.CASES:
            spec = experiment.case_spec(case_name)
            self.assertEqual(spec["schema_version"], "matrouter.paper-case-spec/13")
            self.assertEqual(spec["stage_1"], expected_stage)
            self.assertEqual(
                spec["shared_discovery_policy"], experiment.SHARED_DISCOVERY_POLICY
            )
            self.assertEqual(spec["research_question_ids"], ["RQ1", "RQ2", "RQ3"])

    def test_discovery_constraints_omit_product_engineering_ceiling_overrides(
        self,
    ) -> None:
        constraints = experiment._constraints(all_qualified=True)
        self.assertEqual(constraints.sources, ())
        self.assertEqual(constraints.retrieval.record_scope, "exhaust_upstream")
        self.assertNotIn("limit", constraints.model_fields_set)
        self.assertNotIn("prefer_no_api_key", constraints.model_fields_set)
        self.assertEqual(constraints.retrieval.model_fields_set, {"record_scope"})
        self.assertEqual(
            constraints.model_dump(mode="json", exclude_unset=True),
            {
                "sources": [],
                "retrieval": {"record_scope": "exhaust_upstream"},
                "filters": [],
            },
        )
        request_payload = constraints.model_dump(mode="json", exclude_unset=True)
        serialized_request = experiment.canonical_json(request_payload)
        for field in ("limit", "max_pages", "max_elapsed_seconds", "max_bytes"):
            self.assertNotIn(f'"{field}"', serialized_request)

    def test_no_evaluation_discovery_ceiling_constant_remains(self) -> None:
        source = (ROOT / "experiment.py").read_text()
        self.assertNotIn("SOURCE_RECORD_SAFETY_LIMIT", source)
        self.assertNotIn("DISCOVERY_RECORD_CEILING", source)
        self.assertNotIn("DISCOVERY_RETRIEVAL", source)
        self.assertNotIn("THERMOCHEMICAL_LIMIT", source)
        self.assertNotIn("limit=", source)
        for case_name in experiment.CASES:
            spec_text = (ROOT / "cases" / f"{case_name}.json").read_text()
            self.assertNotIn("record_safety_limit", spec_text)
            self.assertNotIn("max_pages_per_route", spec_text)
            self.assertNotIn("max_normalized_bytes_per_route", spec_text)
            self.assertNotIn('"entry_limit"', spec_text)

    def test_lifepo4_thermochemical_default_contract_executes_without_override(
        self,
    ) -> None:
        from matrouter.adapters.materials_project import MaterialsProjectAdapter
        from matrouter.evidence_contracts import (
            MAX_THERMOCHEMICAL_ENTRY_SET_ENTRIES,
            ScientificArtifactItem,
            SourceFilter,
        )
        from matrouter.evidence_contracts import canonical_json as matrouter_json
        from matrouter.router import MatRouter
        from matrouter.tools.evidence import BeginEvidenceRunRequest, EvidenceTools
        from matrouter.tools.run_state import SessionRunRegistry
        from pymatgen.core import Composition

        observed_queries: list[dict[str, object]] = []

        class FixtureEntry:
            def __init__(self, entry_id: str, formula: str, energy: float) -> None:
                self.entry_id = entry_id
                self.composition = Composition(formula)
                self.uncorrected_energy = energy
                self.correction = 0.0
                self.energy = energy
                self.data = {
                    "material_id": entry_id,
                    "thermo_type": experiment.THERMO_TYPE,
                }

            def as_dict(self) -> dict[str, object]:
                return {
                    "@module": "pymatgen.entries.computed_entries",
                    "@class": "ComputedEntry",
                    "energy": self.energy,
                    "composition": self.composition.as_dict(),
                    "entry_id": self.entry_id,
                    "correction": self.correction,
                    "parameters": {},
                    "data": self.data,
                }

        class FixtureClient:
            db_version = "fixture-database"

            def get_entries_in_chemsys(
                self,
                chemical_system: str,
                **kwargs: object,
            ) -> list[FixtureEntry]:
                self.chemical_system = chemical_system
                self.kwargs = kwargs
                return [
                    FixtureEntry("fixture-Li", "Li", -1.0),
                    FixtureEntry("fixture-LiFePO4", "LiFePO4", -10.0),
                ]

        fixture_client = FixtureClient()

        class FixtureAdapter(MaterialsProjectAdapter):
            def _client(self) -> FixtureClient:  # type: ignore[override]
                return fixture_client

            def get_thermochemical_entries(self, query: object) -> dict[str, object]:
                self.assert_query_mapping(query)
                observed_queries.append(dict(query))
                return super().get_thermochemical_entries(query)  # type: ignore[arg-type]

            @staticmethod
            def assert_query_mapping(query: object) -> None:
                if not isinstance(query, dict):
                    raise TypeError("fixture expected one query mapping")

        adapter = FixtureAdapter(api_key="fixture")
        router = MatRouter([adapter])
        try:
            tools = EvidenceTools(router, SessionRunRegistry())
            run = tools.begin_evidence_run(BeginEvidenceRunRequest())
            source_filter = SourceFilter(
                source="materials_project",
                filter_json=matrouter_json({"thermo_types": [experiment.THERMO_TYPE]}),
            )
            requirement = experiment._create_requirement(
                tools,
                run.evidence_run_id,
                subject=experiment._subject(elements=("Fe", "Li", "O", "P")),
                kind="thermochemical_entries",
                constraints=experiment._constraints(
                    sources=("materials_project",),
                    filters=(source_filter,),
                ),
            )
            self.assertNotIn(
                "limit", requirement.operational_constraints.model_fields_set
            )
            routes = experiment._route(tools, run.evidence_run_id, requirement)
            selected = [
                route
                for route in routes
                if route.is_ready and route.operation == "get_thermochemical_entries"
            ]
            self.assertEqual(len(selected), 1)
            acquisition = experiment._execute(
                tools,
                run.evidence_run_id,
                requirement,
                selected[0],
                "fixture-lifepo4-default-thermochemical",
            )
            self.assertEqual(acquisition.outcome.execution_status, "succeeded")
            self.assertEqual(acquisition.outcome.record_completeness.state, "complete")
            self.assertEqual(len(observed_queries), 1)
            self.assertEqual(
                observed_queries[0]["limit"],
                MAX_THERMOCHEMICAL_ENTRY_SET_ENTRIES,
            )
            bundle = experiment._assemble_run(
                tools,
                run.evidence_run_id,
                [requirement],
                [acquisition],
            )
            entry_sets = [
                item
                for item in bundle.evidence_items
                if isinstance(item, ScientificArtifactItem)
                and item.artifact_type == "thermochemical_entry_set"
            ]
            self.assertEqual(len(entry_sets), 1)
        finally:
            router.close()

    def test_formal_capture_is_enabled_for_v0102(self) -> None:
        self.assertTrue(experiment.FORMAL_CAPTURE_ENABLED)
        self.assertEqual(
            experiment.FINAL_RELEASE_BINDING,
            {
                "package_version": "0.10.2",
                "public_VERSION": "0.10.2",
                "release_tag": "v0.10.2",
            },
        )

    def test_run_is_atomic_and_forbids_selective_repair(self) -> None:
        source = inspect.getsource(experiment.run_all)
        self.assertIn("for case_index, case_name in enumerate(CASES", source)
        self.assertIn("all_cases_captured_once", source)
        self.assertIn('"selective_rerun": False', source)
        self.assertIn("staging_directory.rename(final_raw_directory)", source)
        self.assertIn("rerun all three cases from the beginning", source)

    def test_invalidated_attempt_has_a_small_noncanonical_marker(self) -> None:
        markers = list((ROOT / "raw" / "invalidated" / "0.10.0").glob("*.json"))
        self.assertEqual(len(markers), 1)
        marker = experiment.load_json(markers[0])
        self.assertEqual(marker["status"], "invalidated_noncanonical_capture")
        self.assertFalse(marker["canonical_use_permitted"])
        self.assertFalse(marker["raw_capture_retained"])

    def test_primary_discovery_calls_public_aggregate_exactly_once(self) -> None:
        source = inspect.getsource(experiment.acquire_authoritative_discovery)
        self.assertEqual(source.count(".aggregate_source_records("), 1)
        self.assertNotIn("_execute(", source)
        self.assertIn('"bundle_role": "primary_aggregate"', source)
        self.assertIn('"canonical_bundle": primary_bundle', source)

    def test_case_orchestration_has_one_discovery_entry_and_no_search_loop(
        self,
    ) -> None:
        source = inspect.getsource(experiment.acquire_case)
        self.assertEqual(source.count("acquire_authoritative_discovery("), 1)
        self.assertNotIn('kind="source_record"', source)
        self.assertNotIn("BeginEvidenceRunRequest", source)
        self.assertIn("case_tools", source)
        self.assertIn("case_run_id", source)
        self.assertIn("discovery_acquisitions", source)
        self.assertIn("case_acquisitions.extend(acquisitions)", source)
        self.assertIn("case_acquisitions.extend(thermo_acquisitions)", source)
        self.assertGreaterEqual(source.count("case_requirements,\n"), 2)
        self.assertGreaterEqual(source.count("case_acquisitions,\n"), 2)

    def test_execute_guard_rejects_source_search(self) -> None:
        tools = Mock()
        with self.assertRaisesRegex(ValueError, "owned exclusively"):
            experiment._execute(
                tools,
                "run:00000000-0000-0000-0000-000000000000",
                Mock(),
                Mock(operation="search_materials"),
                "attempt",
            )
        tools.execute_evidence_route.assert_not_called()

    def test_product_aggregate_retains_bounded_ordered_parallel_fanout(self) -> None:
        from matrouter._parallel import MAX_PARALLEL_SOURCE_CALLS, ordered_parallel_map
        from matrouter.tools.evidence import EvidenceTools

        self.assertEqual(MAX_PARALLEL_SOURCE_CALLS, 8)
        self.assertIn(
            "ordered_parallel_map",
            inspect.getsource(EvidenceTools.aggregate_source_records),
        )
        self.assertEqual(
            ordered_parallel_map(lambda value: value * 2, (3, 1, 2)), (6, 2, 4)
        )

    def test_authoritative_discovery_fixture_has_one_bundle_and_one_record_total(
        self,
    ) -> None:
        from matrouter.retrieval import AdapterSearchResult, RecordCompleteness
        from matrouter.router import MatRouter
        from matrouter.source_manifest import Access, AdapterManifest, RouteOperation

        class Adapter:
            def __init__(self, name: str, count: int) -> None:
                self.NAME = name
                self._records = tuple(
                    {
                        "source": name,
                        "source_id": f"{name}-{index}",
                        "formula": "Si",
                        "elements": ["Si"],
                        "source_metadata": {"provider": name},
                    }
                    for index in range(count)
                )

            @property
            def manifest(self) -> AdapterManifest:
                return AdapterManifest(
                    name=self.NAME,
                    endpoint=f"https://{self.NAME}.example",
                    targets=("material",),
                    operations={RouteOperation.SEARCH_MATERIALS: Access.PUBLIC},
                )

            def search(self, query: dict[str, object]) -> AdapterSearchResult:
                return AdapterSearchResult(
                    records=self._records,
                    completeness=RecordCompleteness(
                        state="complete",
                        returned_count=len(self._records),
                        upstream_total=len(self._records),
                        pages_fetched=1,
                        exhaustion_evidence="fixture_exhausted",
                    ),
                )

        router = MatRouter([Adapter("fixture_a", 3), Adapter("fixture_b", 2)])  # type: ignore[arg-type]
        try:
            ledger = experiment.acquire_authoritative_discovery(
                router, case_name="synthetic", formula="Si"
            )
        finally:
            router.close()
        self.assertEqual(ledger["aggregate_source_records_call_count"], 1)
        self.assertEqual(len(ledger["bundle_capsules"]), 1)
        self.assertEqual(len(ledger["discovery_acquisitions"]), 2)
        self.assertEqual(ledger["primary_summary"]["source_record_count"], 5)
        reassembled = experiment._assemble_run(
            ledger["tools"],
            ledger["run"].evidence_run_id,
            [ledger["discovery_requirement"]],
            ledger["discovery_acquisitions"],
        )
        self.assertEqual(
            reassembled.bundle_id, ledger["primary_bundle_model"].bundle_id
        )
        with self.assertRaisesRegex(ValueError, "include every attempt"):
            experiment._assemble_run(
                ledger["tools"],
                ledger["run"].evidence_run_id,
                [ledger["discovery_requirement"]],
                ledger["discovery_acquisitions"][:1],
            )
        shared = ledger["shared_discovery_summary"]
        self.assertEqual(shared["source_record_count"], 5)
        self.assertTrue(shared["rq1_rq2_same_bundle"])
        self.assertEqual(shared["additional_source_record_acquisition_count"], 0)
        report = experiment._rq1_rq2_shared_ledger_report(
            [
                {
                    "case_name": "synthetic",
                    "evidence_bundles": ledger["bundle_capsules"],
                    "aggregate": ledger["primary_summary"],
                    "shared_discovery_ledger": shared,
                }
            ]
        )["cases"][0]
        self.assertEqual(
            report["authoritative_bundle_id"], shared["authoritative_bundle_id"]
        )
        self.assertEqual(
            report["shared_discovery_source_record_count"],
            shared["source_record_count"],
        )
        self.assertTrue(report["invariants"]["rq1_rq2_same_bundle"])
        self.assertEqual(report["invariants"]["separate_rq2_retrieval_count"], 0)
        raw = {
            "runs": ledger["raw_runs"],
            "aggregate_source_records_call_count": 1,
            "retrieval_strategy": {
                "shared_discovery_policy": experiment.SHARED_DISCOVERY_POLICY
            },
            "shared_discovery_ledger": shared,
        }
        self.assertTrue(experiment._shared_discovery_capture_audit(raw)["passed"])

    def test_completed_capture_has_one_discovery_ledger_per_case(self) -> None:
        capture_root = ROOT / "raw" / "0.10.2"
        if not capture_root.is_dir():
            self.skipTest("formal v0.10.2 capture is not present")
        for case_name in experiment.CASES:
            raw = experiment.load_json(capture_root / f"{case_name}.json")
            result = experiment.load_json(
                ROOT / "results" / "cases" / f"{case_name}.json"
            )
            self.assertEqual(raw["aggregate_source_records_call_count"], 1)
            self.assertTrue(raw["shared_discovery_ledger"]["rq1_rq2_same_bundle"])
            self.assertEqual(
                raw["shared_discovery_ledger"]["authoritative_bundle_id"],
                result["primary_result_bundle_id"],
            )
            self.assertEqual(
                raw["shared_discovery_ledger"]["source_record_count"],
                result["aggregate"]["source_record_count"],
            )
            discovery_runs = [
                run
                for run in raw["runs"]
                if any(
                    acquisition["route"]["operation"] == "search_materials"
                    for acquisition in run["acquisitions"]
                )
            ]
            self.assertEqual(len(discovery_runs), 1)
            self.assertEqual(discovery_runs[0]["run_role"], "primary_aggregate")

    def test_bound_detail_uses_formula_subject_and_exact_initial_binding(self) -> None:
        source = inspect.getsource(experiment._add_bound_detail)
        self.assertIn("_subject(formula=formula)", source)
        self.assertNotIn("_subject(material_id=", source)
        self.assertIn("input_acquisition=discovery_acquisition", source)
        self.assertIn("input_record_ref=record_ref", source)

    def test_stage2_audit_requires_initial_discovery_binding(self) -> None:
        from matrouter.evidence_contracts import make_source_record_item

        item = make_source_record_item(
            record={
                "source": "fixture",
                "source_id": "fixture-1",
                "source_metadata": {"provider": "fixture"},
            }
        ).model_dump(mode="json", exclude_computed_fields=True)
        record_ref = {
            "source": "fixture",
            "source_id": "fixture-1",
            "record_content_id": "sha256:" + "1" * 64,
        }
        requirement = {
            "requirement_id": "sha256:" + "2" * 64,
            "evidence_kind": "structure",
            "operational_constraints": {"sources": ["fixture"]},
        }
        route = {
            "requirement_id": requirement["requirement_id"],
            "operation": "get_structure",
            "missing_setting": None,
        }
        acquisition = {
            "acquisition_id": "sha256:" + "3" * 64,
            "requirement": requirement,
            "route": route,
            "input_acquisition_id": "sha256:" + "4" * 64,
            "input_record_ref": record_ref,
            "outcome": {"execution_status": "succeeded"},
        }
        raw = {
            "qualified_source_routes": ["fixture"],
            "runs": [
                {
                    "run_role": "primary_aggregate",
                    "acquisitions": [
                        {
                            "acquisition_id": acquisition["input_acquisition_id"],
                            "route": {"operation": "search_materials"},
                            "record_refs": [record_ref],
                        }
                    ],
                    "canonical_bundle": {"evidence_items": [item]},
                },
                {
                    "run_role": "target_followup",
                    "requirements": [requirement],
                    "routes": [route],
                    "acquisitions": [acquisition],
                },
            ],
        }
        spec = {
            "stage_2_targets": [
                {
                    "qualified_source_route": "fixture",
                    "source_id": "fixture-1",
                    "scientific_role": "fixture",
                    "enrichment_routes": [
                        {"evidence_kind": "structure", "operation": "get_structure"}
                    ],
                }
            ]
        }
        self.assertTrue(experiment._stage2_target_audit(raw, spec)["passed"])
        raw["runs"][1]["acquisitions"][0]["input_acquisition_id"] = "sha256:" + "5" * 64
        self.assertFalse(experiment._stage2_target_audit(raw, spec)["passed"])

    def test_assemble_run_deduplicates_content_addressed_ids(self) -> None:
        tools = Mock()
        sentinel = object()
        tools.assemble_evidence_bundle.return_value = sentinel
        requirement_id = "sha256:" + "1" * 64
        acquisition_id = "sha256:" + "2" * 64
        result = experiment._assemble_run(
            tools,
            "run:00000000-0000-0000-0000-000000000000",
            [Mock(requirement_id=requirement_id), Mock(requirement_id=requirement_id)],
            [Mock(acquisition_id=acquisition_id), Mock(acquisition_id=acquisition_id)],
        )
        self.assertIs(result, sentinel)
        request = tools.assemble_evidence_bundle.call_args.args[0]
        self.assertEqual(request.requirement_ids, (requirement_id,))
        self.assertEqual(request.acquisition_ids, (acquisition_id,))

    def test_v0102_bundle_contract_keeps_scientific_items_and_executions_separate(
        self,
    ) -> None:
        from matrouter.evidence_contracts import EvidenceBundle

        self.assertIn("evidence_items", EvidenceBundle.model_fields)
        self.assertIn("executions", EvidenceBundle.model_fields)
        self.assertNotIn("source_outcomes", EvidenceBundle.model_fields)
        identity = experiment.load_json(ROOT / "product-identity.release.json")
        contract = identity["evidence_bundle_contract"]
        self.assertEqual(contract["scientific_items_field"], "evidence_items")
        self.assertTrue(contract["record_result_is_derived_not_stored"])

    def test_record_result_is_derived_from_independent_axes(self) -> None:
        complete_empty = {
            "execution_status": "succeeded",
            "reason_code": "verified_empty_result",
            "failure_type": None,
            "message": None,
            "record_completeness": {
                "state": "complete",
                "returned_count": 0,
                "upstream_total": 0,
                "pages_fetched": 1,
                "last_cursor": None,
                "exhaustion_evidence": "fixture_exhausted",
                "truncation_reason": None,
            },
        }
        failed = {
            "execution_status": "failed",
            "reason_code": "upstream_error",
            "failure_type": "upstream",
            "message": "fixture",
            "record_completeness": None,
        }
        self.assertEqual(
            experiment._derived_record_result(complete_empty, "search_materials"),
            "empty",
        )
        self.assertEqual(
            experiment._derived_record_result(failed, "search_materials"), "failed"
        )

    def test_completeness_audit_uses_captured_product_capacity(self) -> None:
        source = inspect.getsource(experiment._record_completeness_assessment)
        self.assertIn('run_capacity["max_source_records"]', source)
        self.assertIn('run_capacity["max_bundle_canonical_bytes"]', source)
        self.assertNotIn(">= 512", source)
        self.assertNotIn("16_000_000", source)

    def test_rq1_rq2_report_is_shared_identity_not_two_counts(self) -> None:
        source = inspect.getsource(experiment._rq1_rq2_shared_ledger_report)
        self.assertIn("same_executions", source)
        self.assertIn("same_source_record_items", source)
        self.assertIn("separate_rq2_retrieval_count", source)
        self.assertNotIn("delta_rq2", source)

    def test_scientific_exports_read_primary_discovery_records(self) -> None:
        source = inspect.getsource(experiment._paper_scientific_rows)
        self.assertIn("_property_occurrences(primary)", source)
        self.assertNotIn("_rq2_source_record", source)

    def test_preregistered_targets_and_method_applicability_are_preserved(self) -> None:
        mos2 = experiment.case_spec("mos2-band-gap")
        self.assertEqual(
            [
                (target["qualified_source_route"], target["source_id"])
                for target in mos2["stage_2_targets"]
            ],
            [
                ("c2db", "1MoS2-1"),
                ("materials_project", "mp-2815"),
                (
                    "aflow",
                    "aflowlib.duke.edu:AFLOWDATA/ICSD_WEB/HEX/Mo1S2_ICSD_644246",
                ),
            ],
        )
        self.assertEqual(
            set(mos2["rq3_method_applicability"]["expected_method_names"]),
            {
                "match_structures",
                "render_band_structure",
                "render_density_of_states",
            },
        )
        self.assertEqual(
            experiment.case_spec("lifepo4-stability")["stage_2_targets"], []
        )
        self.assertEqual(
            experiment.case_spec("bi2se3-topology")["rq3_method_applicability"][
                "status"
            ],
            "not_applicable",
        )

    def test_mos2_structure_match_deduplicates_cumulative_bundle_items(self) -> None:
        raw_path = ROOT / "raw" / "0.10.2" / "mos2-band-gap.json"
        if not raw_path.is_file():
            self.skipTest("formal v0.10.2 capture is not present")
        method = experiment._match_preregistered_mos2_structures(
            experiment.replay_case("mos2-band-gap", raw_path),
            experiment.case_spec("mos2-band-gap"),
        )
        self.assertIsNotNone(method)
        assert method is not None
        self.assertEqual(method["method_name"], "match_structures")
        self.assertEqual(len(method["exact_input_item_ids"]), 2)
        self.assertEqual(len(set(method["input_bundle_ids"])), 1)

    def test_scientific_guardrails_remain_case_local(self) -> None:
        mos2 = experiment.case_spec("mos2-band-gap")
        lifepo4 = experiment.case_spec("lifepo4-stability")
        bi2se3 = experiment.case_spec("bi2se3-topology")
        self.assertIn("universal MoS2 band gap", mos2["prohibited_statement"])
        self.assertIn("Formation energy is distinct", lifepo4["context_differences"][0])
        self.assertIn("mix sources or energy frames", lifepo4["prohibited_statement"])
        self.assertIn(
            "independently validated topology", bi2se3["prohibited_statement"]
        )

    def test_thermochemical_method_keeps_exact_complete_entry_set_gate(self) -> None:
        source = inspect.getsource(experiment._compute_lifepo4_phase_diagram)
        self.assertIn('artifact_type == "thermochemical_entry_set"', source)
        self.assertIn('!= "complete"', source)
        self.assertIn("entry_set=entry_set", source)

    def test_report_path_is_offline(self) -> None:
        source = inspect.getsource(experiment.report_completed_capture)
        self.assertNotIn("create_router", source)
        self.assertNotIn("preflight(", source)

    def test_docs_describe_v0102_atomic_capture_and_single_ledger(self) -> None:
        readme = (ROOT / "README.md").read_text()
        agents = (ROOT / "AGENTS.md").read_text()
        combined = readme + agents
        self.assertIn("formal v0.10.2 acquisition", readme)
        self.assertIn("atomic", readme)
        self.assertIn("three-case run", readme)
        self.assertIn("RQ1 and RQ2 are deterministic views of the same Bundle", readme)
        self.assertIn("ordered_parallel_map", readme)
        self.assertIn("effective values must be captured at runtime", agents)
        self.assertNotIn("The separate RQ2 layer", combined)

    def test_active_protocol_sources_have_no_retired_dual_retrieval_terms(self) -> None:
        active_text = "\n".join(
            [
                (ROOT / "experiment.py").read_text(),
                (ROOT / "AGENTS.md").read_text(),
                (ROOT / "README.md").read_text(),
                *[
                    (ROOT / "cases" / f"{case_name}.json").read_text()
                    for case_name in experiment.CASES
                ],
            ]
        )
        retired_tokens = (
            "source_record_exhaustion_" + "shard",
            "rq2_" + "shard_count",
            "rq2-source-outcome-audit.csv",
            "rq1-rq2-difference-audit.json",
        )
        for token in retired_tokens:
            self.assertNotIn(token, active_text)

    def test_historical_and_current_raw_release_boundaries(self) -> None:
        self.assertTrue((ROOT / "raw" / "0.9.1").is_dir())
        self.assertTrue((ROOT / "raw" / "0.9.2").is_dir())
        self.assertFalse((ROOT / "raw" / "0.10.0").exists())
        self.assertTrue((ROOT / "raw" / "0.10.1").is_dir())
        current = ROOT / "raw" / "0.10.2"
        if current.is_dir():
            manifest = experiment.load_json(current / "capture-manifest.json")
            self.assertEqual(
                manifest["status"], "complete_immutable_three_case_capture"
            )
            self.assertTrue(manifest["all_cases_captured_once"])
            self.assertFalse(manifest["selective_rerun"])

    def test_source_completeness_review_counts_unique_attempts(self) -> None:
        path = ROOT / "results" / "source-completeness-review.json"
        if not path.is_file():
            self.skipTest("derived completeness review is not present")
        review = experiment.load_json(path)
        attempt_keys = [(row["case_name"], row["attempt_id"]) for row in review["rows"]]
        self.assertEqual(len(attempt_keys), len(set(attempt_keys)))

    def test_invalidated_marker_contains_no_private_path_or_secret_assignment(
        self,
    ) -> None:
        markers = list((ROOT / "raw" / "invalidated").glob("*/*.json"))
        self.assertGreaterEqual(len(markers), 2)
        for marker in markers:
            text = marker.read_text()
            self.assertNotIn(str(Path.home()), text)
            self.assertNotIn("/private/tmp", text)
            for name in (
                "MATROUTER_MP_API_KEY=",
                "MATROUTER_MPDS_API_KEY=",
                "MATROUTER_MG_API_KEY=",
            ):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
