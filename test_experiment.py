from __future__ import annotations

import copy
import csv
import importlib.util
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "paper_experiment", Path(__file__).with_name("experiment.py")
)
assert SPEC and SPEC.loader
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)
ROOT = Path(__file__).resolve().parent


class CapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest_path = ROOT / "results" / "manifest.json"
        cls.manifest = (
            experiment.load_json(manifest_path) if manifest_path.is_file() else None
        )
        if cls.manifest and cls.manifest.get("schema_version") == (
            "matrouter.paper-manifest/10"
        ):
            cls.results = {
                case_name: experiment.load_json(
                    ROOT / "results" / "cases" / f"{case_name}.json"
                )
                for case_name in experiment.CASES
            }
        else:
            cls.manifest = None
            cls.results = {}

    def test_release_identity_is_v090_without_product_epochs(self) -> None:
        identity = experiment.load_json(ROOT / "product-identity.release.json")
        self.assertEqual(identity["package_version"], "0.9.0")
        self.assertEqual(identity["public_VERSION"], "0.9.0")
        self.assertEqual(
            identity["product_commit"],
            "f81296c730769f3a49ca23be0137935f81eef11c",
        )
        self.assertEqual(identity["release_tag"], "v0.9.0")
        self.assertEqual(
            identity["wheel_sha256"],
            "cf8b60a8a0d80872ddeedc65d09331a7b9aaafb0ab704bce14e41c13019b9ab1",
        )
        self.assertEqual(
            identity["sdist_sha256"],
            "81e4418f35bf18fe5047ea21df8efa35eb96f525b1f857de0e23a33f5ea6513b",
        )
        self.assertEqual(identity["core_profile"]["tool_count"], 13)
        self.assertTrue(identity["route_contract"]["route_candidate_output_sources"])
        self.assertEqual(
            identity["route_contract"]["aggregate_max_parallel_source_workers"], 8
        )
        self.assertFalse(
            identity["product_contract_identity"]["matrouter_owned_identity_epochs"]
        )
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

    def test_final_protocol_identity_has_no_fake_epoch(self) -> None:
        self.assertEqual(
            experiment.PROTOCOL_VERSION, "matrouter.paper-three-case-protocol"
        )
        self.assertNotIn("/2", experiment.PROTOCOL_VERSION)

    def test_run_rejects_v081_before_preflight_or_destructive_cleanup(self) -> None:
        identity = {
            "package_version": "0.8.1",
            "public_VERSION": "0.8.1",
            "release_tag": "v0.8.1",
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            temporary_raw = temporary_root / "raw"
            temporary_results = temporary_root / "results"
            old_raw = temporary_raw / "0.8.0" / "preserved.json"
            old_result = temporary_results / "preserved.json"
            experiment.write_json(old_raw, {"sentinel": "old-raw"})
            experiment.write_json(old_result, {"sentinel": "old-result"})
            before = {path: path.read_bytes() for path in (old_raw, old_result)}
            with (
                patch.object(experiment, "RAW", temporary_raw),
                patch.object(experiment, "RESULTS", temporary_results),
                patch.object(
                    experiment, "verify_release_identity", return_value=identity
                ),
                patch.object(experiment, "preflight") as preflight_mock,
                patch.object(experiment, "_clear_retired_active_outputs") as clear_mock,
                self.assertRaisesRegex(
                    RuntimeError, "v0.9.0 release-bound run is pending"
                ),
            ):
                experiment.run_all()
            preflight_mock.assert_not_called()
            clear_mock.assert_not_called()
            self.assertEqual(
                before,
                {path: path.read_bytes() for path in (old_raw, old_result)},
            )

    def test_run_rejects_existing_final_raw_before_destructive_cleanup(self) -> None:
        identity = {
            "package_version": "0.9.0",
            "public_VERSION": "0.9.0",
            "release_tag": "v0.9.0",
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            temporary_raw = temporary_root / "raw"
            temporary_results = temporary_root / "results"
            old_raw = temporary_raw / "0.8.0" / "preserved.json"
            old_result = temporary_results / "preserved.json"
            planned = temporary_raw / "0.9.0" / f"{experiment.CASES[0]}.json"
            experiment.write_json(old_raw, {"sentinel": "old-raw"})
            experiment.write_json(old_result, {"sentinel": "old-result"})
            experiment.write_json(planned, {"sentinel": "existing-target"})
            before = {
                path: path.read_bytes() for path in (old_raw, old_result, planned)
            }
            with (
                patch.object(experiment, "RAW", temporary_raw),
                patch.object(experiment, "RESULTS", temporary_results),
                patch.object(
                    experiment, "verify_release_identity", return_value=identity
                ),
                patch.object(experiment, "preflight") as preflight_mock,
                patch.object(experiment, "_clear_retired_active_outputs") as clear_mock,
                self.assertRaisesRegex(
                    FileExistsError, "no active outputs were cleared"
                ),
            ):
                experiment.run_all()
            preflight_mock.assert_not_called()
            clear_mock.assert_not_called()
            self.assertEqual(
                before,
                {path: path.read_bytes() for path in (old_raw, old_result, planned)},
            )

    def test_exactly_three_named_cases(self) -> None:
        self.assertEqual(
            experiment.CASES,
            ("mos2-band-gap", "lifepo4-stability", "bi2se3-topology"),
        )

    def test_bound_detail_uses_formula_subject_plus_exact_record_binding(self) -> None:
        source = inspect.getsource(experiment._add_bound_detail)
        self.assertIn("_subject(formula=formula)", source)
        self.assertNotIn("_subject(material_id=", source)
        self.assertIn("input_record_ref=record_ref", source)

    def test_three_shared_research_questions_and_preregistered_targets(self) -> None:
        self.assertEqual(
            tuple(experiment.COMMON_RESEARCH_QUESTIONS), ("RQ1", "RQ2", "RQ3")
        )
        self.assertIn(
            "exact same primary aggregate Bundle bytes",
            experiment.COMMON_RESEARCH_QUESTIONS["RQ2"],
        )
        for case_name in experiment.CASES:
            spec = experiment.case_spec(case_name)
            self.assertEqual(spec["research_question_ids"], ["RQ1", "RQ2", "RQ3"])
            self.assertEqual(spec["stage_1"]["source_scope"], "all_qualified")
            self.assertEqual(spec["stage_1"]["record_scope"], "exhaust_upstream")
            self.assertEqual(
                spec["stage_1"]["record_safety_limit_per_route"],
                experiment.SOURCE_RECORD_SAFETY_LIMIT,
            )
            self.assertEqual(spec["stage_1"]["public_bundle_item_limit"], 512)
            self.assertEqual(
                spec["stage_1"]["public_bundle_canonical_byte_limit"], 16_000_000
            )
            self.assertIsInstance(spec["stage_2_targets"], list)
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
        self.assertFalse(mos2["stage_2_targets"][0]["enrichment_routes"])
        self.assertEqual(
            {
                row["operation"]
                for row in mos2["stage_2_targets"][1]["enrichment_routes"]
            },
            {"get_structure", "get_band_structure", "get_density_of_states"},
        )
        self.assertEqual(
            experiment.case_spec("lifepo4-stability")["stage_2_targets"], []
        )

    def test_runner_has_only_preregistered_exact_target_selection(self) -> None:
        source = inspect.getsource(experiment.acquire_case)
        self.assertNotIn("_first_refs_by_source", source)
        self.assertNotIn("mg-35598", source)
        self.assertIn("_all_exact_refs", source)
        self.assertIn("target_specs_by_source", source)
        self.assertIn('target["enrichment_routes"]', source)

    def test_primary_aggregate_uses_public_tool_without_fake_merge(self) -> None:
        source = inspect.getsource(experiment.acquire_case)
        self.assertEqual(source.count(".aggregate_source_records("), 1)
        self.assertIn('"bundle_role": "primary_aggregate"', source)
        self.assertIn('"canonical_bundle": aggregate_bundle', source)
        self.assertNotIn("for source_index, catalog_route", source)

    def test_v090_route_candidate_and_materialsgalaxy_parent_route_semantics(
        self,
    ) -> None:
        from matrouter.evidence_contracts import RouteCandidate

        self.assertIn("output_sources", RouteCandidate.model_fields)
        bundle = {
            "bundle_id": "sha256:synthetic",
            "routes": [
                {
                    "qualified_source": "materialsgalaxy",
                    "output_sources": [
                        "materialsgalaxy:CODX",
                        "materialsgalaxy:topo_crystals",
                    ],
                    "state": "ready",
                }
            ],
            "items": [
                {
                    "item_kind": "source_outcome",
                    "outcome": {
                        "source": "materialsgalaxy",
                        "operation": "search_materials",
                        "status": "succeeded",
                        "reason_code": "source_succeeded",
                        "record_count": 0,
                        "record_completeness": {"state": "complete"},
                    },
                }
            ],
        }
        summary = experiment._aggregate_summary(bundle)
        self.assertEqual(summary["qualified_route_count"], 1)
        self.assertEqual(summary["source_outcome_count"], 1)
        self.assertEqual(
            summary["execution_routes"][0]["output_sources"],
            ["materialsgalaxy:CODX", "materialsgalaxy:topo_crystals"],
        )
        self.assertIn(
            "does not establish a separate child execution outcome",
            summary["materials_galaxy_parent_outcome_semantics"],
        )

    def test_primary_and_target_bundles_remain_separate(self) -> None:
        result = {
            "case_name": "synthetic",
            "evidence_bundles": [
                {
                    "bundle_role": "primary_aggregate",
                    "evidence_bundle": {"bundle_id": "aggregate", "items": []},
                },
                {
                    "bundle_role": "target_followup",
                    "evidence_bundle": {"bundle_id": "target", "items": []},
                },
            ],
        }
        self.assertEqual(
            experiment._primary_aggregate_bundle(result)["bundle_id"], "aggregate"
        )
        self.assertEqual(
            [bundle["bundle_id"] for bundle in experiment._target_bundles(result)],
            ["target"],
        )

    def test_aggregate_requires_records_from_two_sources_and_providers(self) -> None:
        from matrouter.evidence_contracts import make_source_record_item

        def bundle(
            records: list[tuple[str, str | None]], *, include_outcomes: bool = True
        ) -> dict[str, object]:
            sources = sorted({source for source, _ in records} or {"a", "b"})
            items: list[dict[str, object]] = [
                make_source_record_item(
                    record={
                        "source": source,
                        "source_id": f"{source}-1",
                        "source_metadata": {"provider": provider},
                    },
                    payload_type="synthetic.record",
                ).model_dump(mode="json", exclude_computed_fields=True)
                for source, provider in records
            ]
            if include_outcomes:
                items.extend(
                    {
                        "item_kind": "source_outcome",
                        "outcome": {
                            "source": source,
                            "operation": "search_materials",
                            "status": "succeeded",
                            "reason_code": "source_succeeded",
                            "record_count": 1,
                            "record_completeness": {"state": "complete"},
                        },
                    }
                    for source in sources
                )
            return {
                "bundle_id": "sha256:synthetic",
                "routes": [
                    {"qualified_source": source, "state": "ready"} for source in sources
                ],
                "items": items,
            }

        two_sources = experiment._aggregate_summary(
            bundle([("a", "provider-a"), ("b", "provider-b")])
        )
        self.assertTrue(two_sources["real_cross_source_records"])
        self.assertEqual(two_sources["source_record_sources"], ["a", "b"])
        self.assertEqual(two_sources["source_record_source_count"], 2)
        self.assertEqual(
            two_sources["source_record_providers"], ["provider-a", "provider-b"]
        )
        self.assertEqual(two_sources["source_record_provider_count"], 2)

        outcomes_only = experiment._aggregate_summary(bundle([]))
        self.assertFalse(outcomes_only["real_cross_source_records"])
        self.assertEqual(outcomes_only["source_record_source_count"], 0)

        one_source = experiment._aggregate_summary(bundle([("a", "provider-a")]))
        self.assertFalse(one_source["real_cross_source_records"])

        same_provider = experiment._aggregate_summary(
            bundle([("a", "provider-a"), ("b", "provider-a")])
        )
        self.assertTrue(same_provider["source_record_provider_identity_complete"])
        self.assertFalse(same_provider["real_cross_source_records"])

        with self.assertRaisesRegex(ValueError, "source_id"):
            make_source_record_item(
                record={"source": "a"}, payload_type="synthetic.record"
            )
        self.assertIn(
            "aggregate_distinct_provider_count",
            inspect.getsource(experiment.export_results),
        )
        self.assertIn(
            "primary_aggregate_has_real_cross_source_records_each_case",
            inspect.getsource(experiment.write_internal_protocol_review),
        )

    def test_protocol_conformance_uses_cross_source_record_gate(self) -> None:
        from matrouter.evidence_contracts import make_source_record_item

        def raw(record_sources: list[str]) -> dict[str, object]:
            route_sources = ["a", "b"]
            items = [
                make_source_record_item(
                    record={
                        "source": source,
                        "source_id": f"{source}-1",
                        "source_metadata": {"provider": f"provider-{source}"},
                    },
                    payload_type="synthetic.record",
                ).model_dump(mode="json", exclude_computed_fields=True)
                for source in record_sources
            ]
            items.extend(
                {
                    "item_kind": "source_outcome",
                    "outcome": {
                        "source": source,
                        "operation": "search_materials",
                        "status": "succeeded",
                        "reason_code": "source_succeeded",
                        "record_count": 1,
                        "record_completeness": {"state": "complete"},
                    },
                }
                for source in route_sources
            )
            return {
                "protocol_version": experiment.PROTOCOL_VERSION,
                "retrieval_strategy": {},
                "qualified_source_routes": route_sources,
                "runs": [
                    {
                        "run_role": "primary_aggregate",
                        "canonical_bundle": {
                            "bundle_id": "sha256:synthetic",
                            "routes": [
                                {"qualified_source": source, "state": "ready"}
                                for source in route_sources
                            ],
                            "items": items,
                        },
                    },
                ],
            }

        _, passing = experiment._capture_protocol_status(
            raw(["a", "b"]), experiment.case_spec("lifepo4-stability")
        )
        self.assertTrue(passing["single_primary_all_route_aggregate"])
        self.assertTrue(passing["capture_eligible_under_frozen_protocol"])

        _, failing = experiment._capture_protocol_status(
            raw(["a"]), experiment.case_spec("lifepo4-stability")
        )
        self.assertFalse(failing["single_primary_all_route_aggregate"])
        self.assertFalse(failing["capture_eligible_under_frozen_protocol"])

    def test_thermochemical_route_uses_public_2000_entry_seam(self) -> None:
        from matrouter.evidence_contracts import ThermochemicalEntrySetItem
        from matrouter.phase_diagram import (
            MAX_THERMOCHEMICAL_ENTRY_SET_ENTRIES,
            PhaseDiagramDataset,
        )

        self.assertEqual(experiment.THERMOCHEMICAL_LIMIT, 2000)
        self.assertEqual(MAX_THERMOCHEMICAL_ENTRY_SET_ENTRIES, 2000)
        self.assertIs(
            PhaseDiagramDataset.model_fields["entry_set"].annotation,
            ThermochemicalEntrySetItem,
        )
        self.assertNotIn(
            "PhaseDiagramEntry",
            inspect.getsource(experiment._compute_lifepo4_phase_diagram),
        )

    def test_all_qualified_coverage_is_executed(self) -> None:
        if not self.results:
            self.assertEqual(
                experiment.DISCOVERY_RETRIEVAL["record_scope"], "exhaust_upstream"
            )
            return
        expected_sources = {
            row["source"] for row in self.results["mos2-band-gap"]["coverage_matrix"]
        }
        self.assertEqual(
            len(expected_sources),
            self.manifest["capability_preflight"][
                "qualified_aggregate_execution_route_count"
            ],
        )
        for result in self.results.values():
            self.assertEqual(
                {row["source"] for row in result["coverage_matrix"]}, expected_sources
            )
            self.assertTrue(
                all(
                    row["qualified"] and row["executed"]
                    for row in result["coverage_matrix"]
                )
            )

    def test_wildcard_capability_audit_is_release_bound(self) -> None:
        if not self.manifest:
            self.assertEqual(
                experiment.OPTIMADE_WILDCARD_EXCLUSIONS["duplicate"], ["atomgpt"]
            )
            return
        audit = self.manifest["capability_preflight"]
        self.assertTrue(audit["matrouter_optimade_providers_is_wildcard"])
        self.assertTrue(all(audit["credentialed_provider_configuration"].values()))
        self.assertEqual(audit["requires_configuration_pair_count"], 0)
        self.assertGreater(audit["optimade_child_route_count"], 0)
        for snapshots in audit["aggregate_route_snapshots"].values():
            materials_galaxy = [
                row for row in snapshots if row["qualified_source"] == "materialsgalaxy"
            ]
            self.assertEqual(len(materials_galaxy), 1)
            self.assertGreaterEqual(len(materials_galaxy[0]["output_sources"]), 2)
            self.assertFalse(
                any(
                    row["qualified_source"].startswith("materialsgalaxy:")
                    for row in snapshots
                )
            )

    def test_verified_empty_requires_empty_completeness(self) -> None:
        if not self.results:
            self.assertIn(
                "verified_empty", inspect.getsource(experiment._aggregate_coverage_rows)
            )
            return
        for result in self.results.values():
            for row in result["coverage_matrix"]:
                if row["verified_empty"]:
                    self.assertEqual(
                        (row["status"], row["completeness"]), ("empty", "empty")
                    )
                if row["status"] == "failed":
                    self.assertFalse(row["verified_empty"])

    def test_bi2se3_preserves_soc_conditioned_topology(self) -> None:
        spec = experiment.case_spec("bi2se3-topology")
        self.assertIn("source-native", spec["scientific_question"])
        self.assertIn("independently validated topology", spec["prohibited_statement"])
        self.assertTrue(
            any(
                "No cross-source structure matching" in row
                for row in spec["missing_evidence"]
            )
        )
        if self.results:
            result = self.results["bi2se3-topology"]
            self.assertTrue(experiment._bi2se3_topology_pair_present(result))
            rows = experiment._topology_soc_comparison_rows(result)
            self.assertEqual(
                {
                    (
                        row["source_id"],
                        row["source_native_space_group_symbol"],
                        row["soc"],
                        row["materials_galaxy_reported_topology_class"],
                    )
                    for row in rows
                },
                {
                    ("mg-35598", "R-3m", False, "Triv_Ins"),
                    ("mg-35598", "R-3m", True, "TI"),
                    ("mg-2145449", "Pnma", False, "Triv_Ins"),
                    ("mg-2145449", "Pnma", True, "Triv_Ins"),
                },
            )

    def test_mos2_exact_spectral_artifact_is_explicitly_rendered(self) -> None:
        if not self.results:
            spec = experiment.case_spec("mos2-band-gap")
            self.assertEqual(spec["rq3_method_applicability"]["status"], "applicable")
            return
        result = self.results["mos2-band-gap"]
        artifact_ids = experiment._complete_spectral_artifact_ids(result)
        self.assertTrue(artifact_ids)
        self.assertTrue(experiment._successful_spectral_render_input_ids(result))
        self.assertEqual(
            result["case_interpretation"]["retrieved_facts"][
                "explicitly_identified_experimental_band_gap_observation_count"
            ],
            0,
        )
        self.assertEqual(
            sum(
                method["method_name"] == "match_structures"
                and experiment._method_result_succeeded(method)
                for method in result["explicit_methods"]
            ),
            1,
        )

    def test_mos2_eligibility_is_non_vacuous(self) -> None:
        self.assertIn(
            "_mos2_preregistered_methods_are_safe",
            inspect.getsource(experiment._case_paper_eligible),
        )

    def test_rq3_records_per_case_method_applicability(self) -> None:
        expected = {
            "mos2-band-gap": "applicable",
            "lifepo4-stability": "applicable",
            "bi2se3-topology": "not_applicable",
        }
        for case_name, status in expected.items():
            spec = experiment.case_spec(case_name)
            self.assertEqual(spec["rq3_method_applicability"]["status"], status)
        self.assertEqual(
            set(
                experiment.case_spec("mos2-band-gap")["rq3_method_applicability"][
                    "expected_method_names"
                ]
            ),
            {
                "match_structures",
                "render_band_structure",
                "render_density_of_states",
            },
        )
        readme = (ROOT / "README.md").read_text()
        self.assertIn("requires all preregistered methods to succeed", readme)
        self.assertNotIn("requires at least one complete exact band/DOS", readme)
        if self.results:
            self.assertFalse(self.results["bi2se3-topology"]["explicit_methods"])

    def test_lifepo4_exact_entry_set_is_same_bundle_method_input(self) -> None:
        if not self.results:
            source = inspect.getsource(experiment._compute_lifepo4_phase_diagram)
            self.assertIn("ThermochemicalEntrySetItem", source)
            self.assertIn("entry_set=entry_set", source)
            self.assertIn('"exact_input_item_ids": [entry_set.item_id]', source)
            return
        result = self.results["lifepo4-stability"]
        if result["paper_results_eligible"]:
            self.assertTrue(experiment._phase_diagram_method_is_safe(result))
            entry_set = experiment._complete_thermochemical_entry_sets(result)[0]
            self.assertGreater(entry_set["entry_count"], 0)
            rows = experiment._phase_diagram_export_rows(result)
            self.assertEqual(len(rows), entry_set["entry_count"])
            self.assertTrue(
                all(
                    isinstance(row["energy_above_hull_eV_per_atom"], float)
                    and row["thermo_type"] == experiment.THERMO_TYPE
                    and "compatibility-mixed" in row["energy_frame_description"]
                    and "not DFT uncertainty" in row["tolerance_semantics"]
                    for row in rows
                )
            )
        else:
            outcomes = experiment._thermochemical_outcomes(result)
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["status"], "failed")
            self.assertFalse(
                any(
                    method["method_name"] == "compute_phase_diagrams"
                    for method in result["explicit_methods"]
                )
            )
            self.assertTrue(
                (
                    ROOT
                    / "results"
                    / "diagnostics"
                    / "thermochemical-entry-set-typed-reproduction.json"
                ).is_file()
            )

    def test_lifepo4_gate_rejects_incomplete_or_rebound_input(self) -> None:
        self.assertIn(
            '!= "complete"',
            inspect.getsource(experiment._compute_lifepo4_phase_diagram),
        )
        if not self.results:
            return
        result = self.results["lifepo4-stability"]
        if not experiment._phase_diagram_method_is_safe(result):
            self.assertFalse(result["paper_results_eligible"])
            return
        candidate = copy.deepcopy(result)
        for capsule in candidate["evidence_bundles"]:
            for item in capsule["evidence_bundle"]["items"]:
                if (
                    item["item_kind"] == "source_outcome"
                    and item["outcome"]["operation"] == "get_thermochemical_entries"
                ):
                    item["outcome"]["record_completeness"]["state"] = "truncated"
        self.assertFalse(experiment._phase_diagram_method_is_safe(candidate))
        candidate = copy.deepcopy(result)
        phase = next(
            method
            for method in candidate["explicit_methods"]
            if method["method_name"] == "compute_phase_diagrams"
        )
        phase["exact_input_item_ids"] = ["sha256:not-in-bundle"]
        self.assertFalse(experiment._phase_diagram_method_is_safe(candidate))

    def test_validate_rejects_missing_manifest_and_wrong_experiment_identity(
        self,
    ) -> None:
        identity = experiment.load_json(ROOT / "product-identity.release.json")
        with tempfile.TemporaryDirectory() as directory:
            temporary_results = Path(directory)
            with (
                patch.object(experiment, "RESULTS", temporary_results),
                patch.object(
                    experiment, "verify_release_identity", return_value=identity
                ),
                self.assertRaisesRegex(FileNotFoundError, "run is pending"),
            ):
                experiment.validate()
            experiment.write_json(
                temporary_results / "manifest.json",
                {"experiment_id": "wrong-experiment"},
            )
            with (
                patch.object(experiment, "RESULTS", temporary_results),
                patch.object(
                    experiment, "verify_release_identity", return_value=identity
                ),
                self.assertRaisesRegex(ValueError, "identity mismatch"),
            ):
                experiment.validate()
            experiment.write_json(
                temporary_results / "manifest.json",
                {
                    "experiment_id": experiment.experiment_id(identity),
                    "release_identity": {"package_version": "wrong-release"},
                },
            )
            with (
                patch.object(experiment, "RESULTS", temporary_results),
                patch.object(
                    experiment, "verify_release_identity", return_value=identity
                ),
                self.assertRaisesRegex(ValueError, "release identity mismatch"),
            ):
                experiment.validate()

    def test_projection_is_same_bundle_source_record_occurrence_counterfactual(
        self,
    ) -> None:
        source = (ROOT / "experiment.py").read_text()
        for forbidden in (
            "exact_evidence_bundle_count",
            "per_source_closure",
        ):
            self.assertNotIn(forbidden, source)
        source_record = {
            "item_id": "source-record-1",
            "item_kind": "source_record",
            "record_json": experiment.canonical_json(
                {
                    "formula": "MoS2",
                    "source": "container-a",
                    "source_id": "record-a",
                    "property_observations": {
                        "beta_property": {
                            "observations": [
                                {
                                    "value": 3.0,
                                    "unit": "eV",
                                    "provenance": {
                                        "evidence_source": "observation-source",
                                        "evidence_source_id": "observation-3",
                                    },
                                },
                                {
                                    "value": 2.0,
                                    "unit": "eV",
                                    "provenance": {
                                        "evidence_source": "observation-source",
                                        "evidence_source_id": "observation-2",
                                    },
                                },
                                {
                                    "value": 2.0,
                                    "unit": "eV",
                                    "provenance": {
                                        "evidence_source": "observation-source",
                                        "evidence_source_id": "observation-2",
                                    },
                                },
                            ]
                        },
                        "alpha_property": {
                            "value": 1.0,
                            "unit": "eV/atom",
                            "provenance": {},
                        },
                    },
                }
            ),
        }
        no_observation_record = {
            "item_id": "source-record-2",
            "item_kind": "source_record",
            "record_json": experiment.canonical_json(
                {
                    "formula": "Bi2Se3",
                    "source": "container-b",
                    "source_id": "record-b",
                }
            ),
        }
        null_record = {
            "item_id": "source-record-3",
            "item_kind": "source_record",
            "record_json": experiment.canonical_json(
                {
                    "source": "container-c",
                    "source_id": "record-c",
                    "property_observations": {"gamma_property": {}},
                }
            ),
        }
        bundle = {
            "bundle_id": "sha256:" + "a" * 64,
            "requirements": [{"requirement_id": "r1"}],
            "routes": [{"qualified_source": "source-a"}],
            "items": [
                source_record,
                no_observation_record,
                null_record,
                {"item_kind": "structure"},
                {"item_kind": "source_outcome"},
            ],
        }
        projection = experiment._common_record_projection(bundle)
        self.assertIn(
            "_normalized_property_occurrences",
            inspect.getsource(experiment._common_record_projection),
        )
        self.assertIn(
            "_normalized_property_occurrences",
            inspect.getsource(experiment._paper_scientific_rows),
        )
        self.assertEqual(projection["source_bundle_id"], bundle["bundle_id"])
        self.assertEqual(
            projection["source_bundle_canonical_sha256"],
            experiment.sha256_bytes(experiment.canonical_bytes(bundle)),
        )
        self.assertEqual(projection["row_count"], 5)
        self.assertEqual(
            [row["property"] for row in projection["rows"]],
            [
                "alpha_property",
                "beta_property",
                "beta_property",
                "beta_property",
                "gamma_property",
            ],
        )
        self.assertEqual(
            [row["value"] for row in projection["rows"]], [1.0, 3.0, 2.0, 2.0, None]
        )
        self.assertEqual(projection["rows"][0]["source"], "container-a")
        self.assertEqual(projection["rows"][0]["source_id"], "record-a")
        self.assertEqual(projection["rows"][1]["source"], "observation-source")
        self.assertEqual(projection["rows"][1]["source_id"], "observation-3")
        self.assertEqual(projection["rows"][2], projection["rows"][3])
        self.assertIsNone(projection["rows"][4]["formula"])
        self.assertIsNone(projection["rows"][4]["value"])
        self.assertIsNone(projection["rows"][4]["unit"])
        self.assertEqual(
            projection["dropped_non_source_record_item_kind_counts"],
            {"source_outcome": 1, "structure": 1},
        )
        self.assertEqual(
            set(projection["information_loss_categories"]),
            {"execution", "completeness", "context", "provenance", "artifacts"},
        )
        self.assertIsNone(projection["scores"])
        if self.results:
            self.assertTrue(
                all(
                    result["common_record_projection"]["row_count"] > 0
                    for result in self.results.values()
                )
            )

    def test_independent_review_is_non_vacuous_for_applicable_methods(self) -> None:
        source = inspect.getsource(experiment.write_internal_protocol_review)
        self.assertIn(
            "lifepo4_complete_exact_entry_set_and_result_manifest_binding", source
        )
        self.assertIn("_phase_diagram_method_is_safe", source)
        self.assertIn("stage_2_target_audit", source)
        self.assertIn("preregistered_exact_target_followups_succeed", source)
        self.assertIn("applicable_methods_bind_declared_exact_bundle_inputs", source)

    def test_stage2_legacy_every_record_path_is_absent(self) -> None:
        source = (ROOT / "experiment.py").read_text()
        for forbidden in (
            "stage_2_routes",
            "every_stage_1_exact_record",
            "stage_2_preregistered_for_every_returned_record",
            "is_current_protocol_capture",
        ):
            self.assertNotIn(forbidden, source)

    def test_stage2_target_audit_field_is_the_single_conformance_key(self) -> None:
        raw = {
            "qualified_source_routes": ["materials_project"],
            "runs": [
                {
                    "run_role": "primary_aggregate",
                    "canonical_bundle": {
                        "bundle_id": "sha256:synthetic",
                        "routes": [],
                        "items": [],
                    },
                }
            ],
        }
        audit = experiment._stage2_target_audit(
            raw, experiment.case_spec("lifepo4-stability")
        )
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["preregistered_target_count"], 0)
        source = inspect.getsource(experiment._capture_protocol_status)
        self.assertIn('conformance["stage_2_target_audit"]', source)
        audit_source = inspect.getsource(experiment._stage2_target_audit)
        self.assertIn('row.get("input_record_ref")', audit_source)
        self.assertNotIn('row["subject_scope"].get("material_id")', audit_source)

    def test_exact_target_audit_uses_only_preregistered_followups(self) -> None:
        targets = experiment.case_spec("bi2se3-topology")["stage_2_targets"]
        records = [
            {
                "item_kind": "source_record",
                "record_json": experiment.canonical_json(
                    {
                        "source": target["qualified_source_route"],
                        "source_id": target["source_id"],
                    }
                ),
            }
            for target in targets
        ]
        requirements = []
        routes = []
        acquisitions = [
            {
                "requirement": {
                    "requirement_id": "discovery",
                    "evidence_kind": "source_record",
                },
                "route": {"operation": "search_materials"},
                "outcome_draft": {"status": "succeeded"},
                "record_refs": [
                    {
                        "source": target["qualified_source_route"],
                        "source_id": target["source_id"],
                    }
                    for target in targets
                ],
            }
        ]
        for target in targets:
            for index, route_spec in enumerate(target["enrichment_routes"]):
                requirement_id = f"req-{target['source_id']}-{index}"
                requirements.append(
                    {
                        "requirement_id": requirement_id,
                        "evidence_kind": route_spec["evidence_kind"],
                        "operational_constraints": {
                            "sources": [target["qualified_source_route"]]
                        },
                    }
                )
                routes.append(
                    {
                        "requirement_id": requirement_id,
                        "operation": route_spec["operation"],
                        "state": "ready",
                    }
                )
                acquisitions.append(
                    {
                        "requirement": {
                            "requirement_id": requirement_id,
                            "evidence_kind": route_spec["evidence_kind"],
                        },
                        "route": {"operation": route_spec["operation"]},
                        "input_record_ref": {
                            "source": target["qualified_source_route"],
                            "source_id": target["source_id"],
                        },
                        "outcome_draft": {"status": "succeeded"},
                    }
                )
        raw = {
            "qualified_source_routes": ["materialsgalaxy:topo_crystals"],
            "runs": [
                {
                    "run_role": "primary_aggregate",
                    "canonical_bundle": {
                        "bundle_id": "sha256:aggregate",
                        "routes": [],
                        "items": records,
                    },
                },
                {
                    "run_role": "target_followup",
                    "requirements": requirements,
                    "routes": routes,
                    "acquisitions": acquisitions,
                },
            ],
        }
        audit = experiment._stage2_target_audit(
            raw, experiment.case_spec("bi2se3-topology")
        )
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["found_target_count"], 2)
        self.assertEqual(audit["succeeded_enrichment_route_count"], 4)
        self.assertEqual(audit["target_followup_run_count"], 1)

    def test_product_blocker_classifier_is_source_independent_and_narrow(self) -> None:
        def outcome(source: str, reason: str, message: str) -> dict[str, object]:
            return {
                "source": source,
                "operation": "search_materials",
                "status": "failed",
                "reason_code": reason,
                "message": {"present": True, "value": message},
            }

        blockers = experiment._diagnose_stage1_product_blockers(
            "synthetic-case",
            [
                outcome(
                    "optimade:example",
                    "adapter_exception",
                    "RecordCompleteness validation error",
                ),
                outcome(
                    "nomad", "upstream_http_error", "HTTP 422 Unprocessable Entity"
                ),
                outcome("mpds", "upstream_http_error", "HTTP 402 Payment Required"),
                outcome("oqmd-timeout", "upstream_timeout", "request timed out"),
                outcome(
                    "oqmd-502", "upstream_http_unavailable", "HTTP 502 Bad Gateway"
                ),
            ],
        )
        self.assertEqual(
            {(row["source"], row["diagnostic_category"]) for row in blockers},
            {
                ("optimade:example", "adapter_exception"),
                (
                    "nomad",
                    "non_authorization_http_4xx_requires_product_investigation",
                ),
            },
        )
        self.assertEqual({row["http_status"] for row in blockers}, {None, 422})

    def test_unresolved_product_blocker_overrides_positive_case_gate(self) -> None:
        candidate = {
            "case_name": "bi2se3-topology",
            "protocol_conformance": {"capture_eligible_under_frozen_protocol": True},
            "aggregate": {"bundle_id": "sha256:aggregate"},
            "unresolved_product_blockers": [{"blocker_id": "synthetic"}],
        }
        self.assertFalse(experiment._case_paper_eligible(candidate))

    def test_mos2_highlight_derives_structure_match_from_method_result(self) -> None:
        if not self.results:
            return
        candidate = copy.deepcopy(self.results["mos2-band-gap"])
        highlight = experiment._paper_highlights(candidate)
        self.assertTrue(highlight["explicit_structure_matching_performed"])
        self.assertTrue(highlight["explicit_structure_match"]["matched"])
        candidate["explicit_methods"] = [
            method
            for method in candidate["explicit_methods"]
            if method["method_name"] != "match_structures"
        ]
        self.assertFalse(
            experiment._paper_highlights(candidate)[
                "explicit_structure_matching_performed"
            ]
        )

    def test_mos2_preregistered_exact_structure_match_executes_offline(self) -> None:
        if not self.results:
            return
        result = experiment._match_preregistered_mos2_structures(
            self.results["mos2-band-gap"]["evidence_bundles"],
            experiment.case_spec("mos2-band-gap"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result["result"]["matched"])
        self.assertEqual(
            result["result"]["distance_status"],
            "not_computed_for_symmetric_or_skip_reduction_fit",
        )
        self.assertEqual(
            result["result"]["parameters"],
            experiment.case_spec("mos2-band-gap")["explicit_structure_method"][
                "parameters"
            ],
        )
        self.assertEqual(len(result["input_bundle_ids"]), 2)
        self.assertEqual(len(result["exact_input_item_ids"]), 2)

    def test_bi2se3_phase_equivalence_wording_is_case_local(self) -> None:
        if not self.results:
            return
        rows = experiment._topology_soc_comparison_rows(self.results["bi2se3-topology"])
        self.assertTrue(
            all("in the Bi2Se3 case" in row["phase_equivalence_status"] for row in rows)
        )

    def test_csv_json_summary_consistency(self) -> None:
        if not self.results:
            self.assertIn(
                "figure-ready.json", inspect.getsource(experiment.export_results)
            )
            return
        with (ROOT / "results" / "cases.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        figure = experiment.load_json(ROOT / "results" / "figure-ready.json")
        self.assertEqual([row["case_name"] for row in rows], list(experiment.CASES))
        self.assertEqual(
            [row["case_name"] for row in figure["cases"]], list(experiment.CASES)
        )
        self.assertIn(
            "_validate_paper_observation_projection_consistency",
            inspect.getsource(experiment.validate),
        )
        with (ROOT / "results" / "observations.csv").open(newline="") as handle:
            observation_rows = list(csv.DictReader(handle))
        figure_cases = {row["case_name"]: row for row in figure["cases"]}
        for case_name in experiment.CASES:
            projection_rows = self.results[case_name]["common_record_projection"][
                "rows"
            ]
            csv_projection_rows = [
                {
                    "source": row["source"],
                    "source_id": row["source_id"],
                    "formula": row["formula"] or None,
                    "property": row["property"],
                    "value": json.loads(row["value_json"]),
                    "unit": row["unit"] or None,
                }
                for row in observation_rows
                if row["case_name"] == case_name
            ]
            figure_projection_rows = [
                {
                    "source": row["source"],
                    "source_id": row["source_id"],
                    "formula": row["formula"],
                    "property": row["property"],
                    "value": json.loads(row["value_json"]),
                    "unit": row["unit"],
                }
                for row in figure_cases[case_name]["observations"]
            ]
            self.assertEqual(csv_projection_rows, projection_rows)
            self.assertEqual(figure_projection_rows, projection_rows)
            self.assertEqual(
                len(figure_cases[case_name]["observations"]),
                self.results[case_name]["common_record_projection"]["row_count"],
            )
        jarvis_rows = [
            row
            for row in observation_rows
            if row["case_name"] == "mos2-band-gap"
            and row["property"] == "band_gap_eV"
            and row["source_id"].startswith("JVASP-228#field=")
        ]
        self.assertEqual(
            [row["source_id"] for row in jarvis_rows],
            [
                "JVASP-228#field=mbj_bandgap",
                "JVASP-228#field=optb88vdw_bandgap",
            ],
        )
        self.assertEqual([row["value_json"] for row in jarvis_rows], ["0.0", "0.0"])
        self.assertTrue(all("qualified_route_count" in row for row in rows))
        self.assertTrue(all("qualified_source_count" not in row for row in rows))
        with (ROOT / "results" / "phase-diagram-entries.csv").open(
            newline=""
        ) as handle:
            phase_rows = list(csv.DictReader(handle))
        with (ROOT / "results" / "topology-soc-comparison.csv").open(
            newline=""
        ) as handle:
            topology_rows = list(csv.DictReader(handle))
        self.assertEqual(len(phase_rows), 974)
        self.assertEqual(len(topology_rows), 4)
        self.assertFalse((ROOT / "results" / "provider-database-scopes.csv").is_file())
        self.assertEqual(
            figure["paper_results_eligibility_semantics"],
            experiment.PAPER_ELIGIBILITY_SEMANTICS,
        )

    def test_active_protocol_code_has_no_retired_version_compatibility_branch(
        self,
    ) -> None:
        retired_versions = ("0." + "6.2", "0." + "7.1")
        for path in (
            ROOT / "experiment.py",
            ROOT / "README.md",
            ROOT / "product-identity.release.json",
        ):
            for retired_version in retired_versions:
                self.assertNotIn(retired_version, path.read_text())


if __name__ == "__main__":
    unittest.main()
