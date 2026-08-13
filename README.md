# MatRouter three-case evaluation

This repository contains MatRouter's scientific evaluation. Product code and
tests live in `matrouter`; manuscript text and references live in
`matrouter-paper`. The single-track harness is migrated to the formally
published MatRouter v0.10.2 package and contains exactly three cases: MoS2
electronic evidence, LiFePO4 thermodynamic evidence, and Bi2Se3 source-native
topology evidence. It has no LLM benchmark, expert gold, policy verdict,
weighted score, or additional material case.

The formal v0.10.2 acquisition completed as one fresh release-bound, atomic
three-case run:
`matrouter-0.10.2-full-20260812T234402Z-773b4ee50ec3`. The evaluation does not
own records, pages, elapsed-time, normalized-byte, or Bundle-closure engineering
ceilings: its discovery request declares only `all_qualified +
exhaust_upstream`, while the installed product materializes and returns the
effective engineering contract. The frozen run cannot be repaired by
selectively repeating one case or source.

## Common research questions

- **RQ1:** Within the declared catalog, configuration, scope, and budgets, does
  one all-qualified aggregate attempt every capability-matched route and
  preserve each typed outcome and `RecordCompleteness`?
- **RQ2:** What material-data landscape does that same authoritative aggregate
  Bundle support—sources, data categories, scientific contexts, specialist
  data, completeness, and explicit gaps—and how does that landscape guide the
  next research step?
- **RQ3:** Can an Agent use the aggregate to locate preregistered exact
  source-bound records and artifacts for explicit lightweight methods, while
  making unsupported heavy calculations an explicit external handoff rather
  than a proxy result?

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

## Acquisition protocol

Each case calls `aggregate_source_records` exactly once with one
`source_record + all_qualified + exhaust_upstream` requirement. MatRouter keeps
its product implementation: `ordered_parallel_map` fans out at most eight
independent source routes, results are aggregated in stable route-input order,
and cursor/page traversal within one source remains sequential. The evaluation
does not expand this into a per-source `execute_evidence_route` loop.

The requirement omits records, pages, elapsed-time, and normalized-byte
overrides. MatRouter owns their effective defaults and the Bundle-closure
capacity; the formal capture records the effective serialized constraints
and run capacity rather than promoting them to scientific protocol constants.
Scientific items live in `evidence_items`; each route's outcome and warnings
live in `executions`. `execution_status`, `RecordCompleteness`, and the derived
five-state `record_result` remain independent.

RQ1 and RQ2 are deterministic views of the same Bundle, executions, and
source-record items. RQ1 reports qualified/ready/attempted routes and closure;
RQ2 reports exact source contributions, data categories, scientific context,
specialist data, and gaps. It performs no acquisition of its own, so every case
has one discovery record total and no RQ1/RQ2 retrieval-count discrepancy.

The primary Bundle must contain records from at least two distinct sources and
two distinct providers, and every qualified route must have a typed outcome.
Follow-ups resolve only exact targets preregistered by scientific role and
present in the initial aggregate. Every detail, structure, or artifact attempt
stays in the same case ledger and binds the original discovery acquisition and
record reference; no prerequisite source search is repeated. Follow-up Bundles
feed artifacts and methods but do not supplement the discovery record total.
Route counts are operational coverage, not independent evidence counts.

## Current v0.10.2 result

All three cases are protocol-eligible. Each made exactly one aggregate call and
attempted all 32 ready qualified routes. The authoritative discovery totals are
481 MoS2, 465 LiFePO4, and 152 Bi2Se3 source records. MoS2 and LiFePO4 each have
16 complete, 13 verified-empty, and 3 failed discovery routes; Bi2Se3 has 15
complete, 14 verified-empty, and 3 failed routes. Across discovery plus the
thermochemical record-set follow-up, the audit contains 48 complete, 40
verified-empty, and 9 failed unique attempts, with no truncated or
upstream-total-unknown result.

The three discovery failures shared by all cases are preserved as failures:
MPDS returned HTTP 402 access denial, OQMD returned HTTP 502, and the MPDD
OPTIMADE endpoint disconnected. These are upstream/access limitations, not new
MatRouter defects. Alexandria completed successfully in all three v0.10.2
cases. No product retrieval ceiling or Bundle closure cap was reached; the
largest primary discovery contained 481 source records, and the largest
cumulative Bundle was the 13,739,645-byte LiFePO4 thermochemical Bundle.

LiFePO4 retrieved one complete 974-entry Materials Project
GGA/GGA+U/r2SCAN-compatible entry set in a single exact frame and successfully
ran `compute_phase_diagrams`; `mp-19017-GGA+U` lies on the finite captured hull
at the preregistered 1e-6 eV/atom tolerance. This is a result for that exact
entry set and frame, not a synthesizability claim. MoS2 completed all four exact
follow-ups, rendered the `mp-2815` band and DOS artifacts, and matched the exact
AFLOW/Materials Project structures under the fixed matcher parameters. Bi2Se3
completed all four source-native no-SOC/SOC follow-ups; MaterialsGalaxy reports
the R-3m target as trivial without SOC and TI with SOC, while no independent
topology validation is claimed. The product-blocker audit is empty.

## Prior v0.10.1 result

All three cases attempted all 32 ready qualified routes through one aggregate
call each. The authoritative discovery totals are 466 MoS2, 411 LiFePO4, and
130 Bi2Se3 source records. No discovery execution is truncated or
upstream-total-unknown, and no product retrieval or Bundle-closure ceiling is
reached. MoS2 and Bi2Se3 meet their preregistered case gates. LiFePO4 remains
protocol-ineligible because the product-materialized default `limit=10000`
cannot enter the Materials Project thermochemical query contract, which still
validates `limit<=2000`; the typed failure is preserved and no hull is built.
The four discovery failures shared by all cases—Alexandria connection failure,
MPDS payment-required access denial, OQMD HTTP 502, and the MPDD OPTIMADE
connection failure—remain failed upstream outcomes rather than empty results.

RQ2 is reported as a deterministic source-contribution map and case-task trace.
For every exact record source actually present, it identifies the provider
group, contributing data categories and properties, a stable-order
representative record, scientific context, route outcome, and completeness.
Case claims name their supporting source contributions. The trace does not use
a single-source baseline, completeness score, field count, or scientific-truth
judgment. Bundle identity, provenance, and context remain validation and
attribution mechanisms rather than standalone scientific results.

The checked-in `raw/0.9.1/` and `raw/0.9.2/` directories remain immutable
historical captures. The withdrawn dual-retrieval v0.10.0 attempt is not an
active result; its raw payload was removed and only a structured invalidation
marker remains under `raw/invalidated/0.10.0/`. One pre-capture v0.10.1
evaluation-harness closure failure is likewise reduced to a noncanonical audit
marker. The successful but now historical v0.10.1 capture ran all three cases
from the beginning; it is retained unchanged and is not an active v0.10.2 result.
The 0.9.x Bundle and evaluation layouts have no active compatibility branch.

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

Protocol eligibility and file digests remain internal reproducibility checks;
they are not scientific findings. The internal protocol review is not an AI,
expert, external, or peer review.

## Repository interface

- `experiment.py`: the only run, report, validate, smoke, replay, refresh, and
  verify interface.
- `cases/`: three case specs and scientific boundaries.
- `raw/0.9.1/` and `raw/0.9.2/`: immutable prior release-bound captures.
- `raw/0.10.1/`: immutable prior atomic three-case capture.
- `raw/0.10.2/`: immutable current atomic three-case capture.
- `raw/invalidated/`: small audit markers for noncanonical attempts; no
  invalidated payload is an input to results.
- `results/`: derived case capsules, material-landscape case traces, direct
  analysis CSV/JSON/SVG files, the per-source completeness review, the shared
  RQ1/RQ2 ledger audit, product blockers, and the internal protocol review.
- `results/figure-ready.json`: compact case/task, route-outcome, cross-source
  insight, exact-follow-up, method, handoff, and scientific-boundary summaries;
  detailed records and provenance remain in the case traces and audit exports.
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

`experiment.py report` is applicable only after the complete atomic v0.10.2
capture exists; it never derives from staging, a prior release, or an invalid
attempt.
