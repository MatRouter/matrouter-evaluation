# AGENTS.md

## Scope

This repository owns MatRouter scientific evaluation only. Product code and
tests belong in `../matrouter`; manuscript text belongs in
`../matrouter-paper`. Do not modify, publish, commit, or push either repository
from an evaluation task.

## Active protocol

The repository root contains exactly three cases: MoS2 electronic evidence,
LiFePO4 thermodynamic evidence, and Bi2Se3 source-native topology evidence. The
single active protocol identity is `matrouter.paper-three-case-protocol` and its
harness is release-bound to the formally published MatRouter v0.10.2 identity.
The formal v0.10.2 acquisition is complete and immutable under full-run ID
`matrouter-0.10.2-full-20260812T234402Z-773b4ee50ec3`; never replace, populate,
or repair it through case- or source-selective retries. Canonical
`EvidenceBundle` objects provide stored evidence and exact method inputs; the
scientific result is each case's source-supported material landscape and trace.

- RQ1 asks whether one all-qualified aggregate attempts every capability-matched
  route within the declared catalog, configuration, scope, and budgets, while
  preserving typed outcomes and `RecordCompleteness`.
- RQ2 maps the source-supported material-data landscape: contributing sources,
  data categories, scientific contexts, specialist data, gaps, and the next
  research step. It is not a field-count or scientific-truth metric.
- RQ3 tests whether preregistered exact source-bound records and artifacts enter
  applicable lightweight methods directly, while unsupported heavy calculations
  remain explicit external handoffs. Bi2Se3 has no MatRouter topology validator.

Each case calls `aggregate_source_records` once with `all_qualified +
exhaust_upstream`. MatRouter v0.10.2 performs bounded parallel cross-source
execution with at most eight workers and stable-order aggregation; per-source
pagination remains sequential. The evaluation declares no records, pages,
elapsed-time, normalized-byte, or Bundle-closure ceiling override; those
engineering defaults belong to the installed product release and their
effective values must be captured at runtime. Scientific items are stored in
`evidence_items`; route outcomes and warnings are embedded in `executions`.
Keep `execution_status`, `RecordCompleteness`, and the derived five-state
`record_result` independent.

RQ1 and RQ2 are two views of that same authoritative Bundle and execution
ledger. Never issue an independent top-level or selected-source source-record
run for RQ2, capacity expansion, or supplementation. Exact detail, structure,
artifact, and method-input follow-ups stay in the same case ledger and bind a
preregistered record reference from the initial aggregate; they never repeat a
source search. Keep failed, empty, truncated, and upstream-total-unknown
results distinct. A qualified route count is not an independent evidence count.

## Scientific boundaries

- A ready route is not a successful execution; retrieval is not a universal
  verdict.
- Preserve phase identity, context, provenance, lineage, and artifact binding.
- Do not infer phase identity from formula or hull stability from formation
  energy, and do not mix energy frames.
- A spectral render must consume a complete exact artifact from the same
  Bundle.
- A phase diagram must consume a complete exact single-source, single-frame
  entry set. Failed or incomplete sets never enter the hull.
- Bi2Se3 topology remains source-native and SOC-conditioned, not independently
  validated.
- `paper_results_eligible` means frozen protocol eligibility only, not
  scientific-truth validation. The review artifact is a deterministic internal
  checklist, not independent AI, expert, external, or peer review.

## Execution rules

- Frozen raw packets are immutable replay inputs.
- `raw/0.9.1/` and `raw/0.9.2/` are immutable history. The withdrawn v0.10.0
  attempt retains only a small audit marker under `raw/invalidated/`; it is
  never an input to active results.
- `raw/0.10.1/` is an immutable prior complete run whose LiFePO4 gate exposed
  the thermochemical default/query-limit product defect fixed by v0.10.2. A
  pre-capture evaluation-harness failure retains only a small noncanonical
  marker; its discarded payload is not a result input.
- `raw/0.10.2/` is the completed current atomic three-case capture. It is the
  only raw input to active results and must remain immutable.
- Never selectively rerun unfavorable rows or turn failure into verified empty.
- Load credentials only from the process environment or
  `~/.config/matrouter/env`; never record values, host paths, or caches.
- One full release-bound run is immutable once captured; never selectively rerun
  an individual case or source.

Offline checks:

```bash
uv sync --frozen
uv run python experiment.py validate
uv run python experiment.py verify
uv run python -m unittest test_experiment.py
uv run ruff check .
uv run ruff format --check .
```

Run `uv run python experiment.py report` only after the complete atomic v0.10.2
capture exists; never derive a report from staging, a prior release, or an
invalidated attempt.
