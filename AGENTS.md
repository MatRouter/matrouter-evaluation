# AGENTS.md

## Scope

This repository owns MatRouter scientific evaluation only. Product code and
tests belong in `../matrouter`; manuscript text belongs in
`../matrouter-paper`. Do not modify, publish, commit, or push either repository
from an evaluation task.

## Active protocol

The repository root contains exactly three cases: MoS2 electronic evidence,
LiFePO4 thermodynamic evidence, and Bi2Se3 source-native topology evidence. The
single active protocol identity is `matrouter.paper-three-case-protocol` and is
release-bound to the formally published MatRouter v0.9.0 identity. Canonical
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
exhaust_upstream`. MatRouter v0.9.0 performs bounded parallel cross-source
execution with at most eight workers and stable-order aggregation; per-source
pagination remains sequential, and routes fairly share the public
512-item/16-MB Bundle capacity.
Never issue independent top-level source-record runs to supplement the primary
aggregate. Follow-up Bundles are limited to preregistered exact targets and are
never fabricated into a cross-run Bundle. Keep failed, empty, partial,
truncated, and unknown completeness distinct. A qualified route count is not an
independent evidence count.

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
