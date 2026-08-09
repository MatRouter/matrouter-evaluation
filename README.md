# MatRouter three-case evaluation

This repository contains MatRouter's scientific evaluation. Product code and
tests live in `matrouter`; manuscript text and references live in
`matrouter-paper`. The single active evaluation is bound to the formally
published MatRouter v0.9.0 package and contains exactly three cases: MoS2
electronic evidence, LiFePO4 thermodynamic evidence, and Bi2Se3 source-native
topology evidence. It has no LLM benchmark, expert gold, policy verdict,
weighted score, or additional material case.

## Common research questions

- **RQ1:** does one `all_qualified` aggregate Bundle contain records from
  multiple heterogeneous sources and providers while preserving a typed
  `SourceOutcome` for every qualified route?
- **RQ2:** compared with the deterministic six-field common-record projection
  from the exact same primary Bundle bytes, what execution, completeness,
  context, provenance, and artifact information does the full Bundle preserve?
- **RQ3:** can preregistered exact-target follow-up artifacts enter explicit
  methods directly without hidden requery inside those methods?

RQ3 applicability is recorded in every case spec and result:

- MoS2: `applicable`; requires all preregistered methods to succeed: one exact
  AFLOW-to-Materials-Project structure match with the fixed parameters, one
  render of the exact Materials Project `mp-2815` band artifact, and one render
  of its exact DOS artifact. Every input remains bound to its declared Bundle.
- LiFePO4: `applicable`; requires a complete exact single-source, single-frame
  compatible entry set and a successful `compute_phase_diagrams` result.
- Bi2Se3: `not_applicable`; MatRouter has no general topology-validation method.
  The case tests source-native SOC-conditioned acquisition without claiming a
  method result or independent topology validation.

## Frozen acquisition

Each case calls `aggregate_source_records` exactly once with one
`source_record + all_qualified + exhaust_upstream` requirement. MatRouter v0.9.0
executes qualified routes with at most eight workers, aggregates in stable
order, and assembles one primary cross-source Bundle; pagination within one
source is sequential. The public 512-item/16-MB Bundle limit is fairly shared
across execution routes and is never bypassed. A capacity or safety stop
remains typed `partial` or `truncated`; all qualified routes are attempted, but
the result is not an all-upstream-records claim.

The primary Bundle must contain records from at least two distinct sources and
two distinct providers, and every qualified route must have a typed outcome.
Follow-up runs resolve only exact targets preregistered by scientific role.
Their immutable Bundles feed artifacts and methods but are not merged into the
primary Bundle and do not supplement its headline record count. Route counts
are operational coverage, not independent evidence counts.

The RQ2 common-record projection copies only `source`, `source_id`, `formula`,
`property`, `value`, and `unit` from normalized `property_observations`
occurrences already stored in each primary-Bundle
`SourceRecordItem.record_json`. It preserves Bundle item order, canonical
property-key order, observations-list order, and occurrence multiplicity.
Observation-specific provenance identity takes precedence over the containing
record identity; missing values remain null. It performs no query, filtering,
ranking, remapping, conversion, deduplication, aggregation, or inference.
Non-projectable item kinds produce no pseudo-rows; the companion summary reports
their loss under execution, completeness, context, provenance, and artifact
categories without a score.

## Scientific boundaries

MoS2 retains C2DB `1MoS2-1` only as 2D p-6m2 PBE+SOC source-summary context;
Materials Project `mp-2815` supplies one exact structure, band, and DOS target;
and the preregistered AFLOW ICSD 644246 record supplies the second exact
structure. The AFLOW/MP pair enters one fixed-parameter `match_structures` call,
and the MP band/DOS artifacts are each rendered once. That match applies only
to those two exact bulk structures; other cross-source records, the 2D C2DB
target, and different polytypes remain unmatched. The result is not a unified
or phase-resolved gap answer, and no experimental band-gap observation is
present. Spectral renders are derived views, not additional evidence.

LiFePO4 routes structure, formation energy, and source-native stability. Its
exact Materials Project input is the declared GGA/GGA+U/r2SCAN
compatibility-mixed frame and dataset snapshot, not one functional or
homogeneous DFT method. The 1e-6 eV/atom threshold is only a numerical on-hull
classification tolerance; continuous energy above hull is exported. The result
does not establish finite-temperature stability, universal stability, or
synthesizability.

Bi2Se3 routes structure, band gap, and source-native no-SOC/SOC topology. The
R-3m/Pnma by SOC table reports MaterialsGalaxy data already in the Bundle;
MatRouter did not recompute invariants, surface states, or phase equivalence.

`paper_results_eligible` means only frozen protocol eligibility, not validation
of scientific truth. A ready Stage-1 route with `adapter_exception`, or an
evident non-authorization request/protocol HTTP 400/404/405/422, is an unresolved
product blocker and makes the case ineligible. HTTP 401/402/403 entitlement or
configuration failures, 429, timeouts, 5xx, and ordinary upstream warnings stay
typed but are not automatically called product bugs.
`results/internal-protocol-review.json` is a deterministic internal protocol
and scientific-boundary checklist; it is not independent AI review, expert
adjudication, external review, or peer review.

## Repository interface

- `experiment.py`: the only run, validate, smoke, replay, refresh, and verify
  interface.
- `cases/`: three case specs and scientific boundaries.
- `raw/0.9.0/`: immutable release-bound captures.
- `results/`: derived case capsules, direct paper-analysis CSV/JSON/SVG files,
  product blockers, and the internal protocol review.
- `product-identity.release.json`: verified PyPI release identity.
- `pyproject.toml` and `uv.lock`: non-package uv environment configuration.

Credentials are read only from the process environment or
`~/.config/matrouter/env`. Set up and verify the locked environment with:

```bash
uv sync --frozen
uv run python experiment.py validate
uv run python experiment.py verify
uv run python -m unittest test_experiment.py
uv run ruff check .
uv run ruff format --check .
```
