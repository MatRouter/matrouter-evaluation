# MatRouter three-case evaluation

This repository contains MatRouter's scientific evaluation. Product code and
tests live in `matrouter`; manuscript text and references live in
`matrouter-paper`. The single active evaluation is bound to the formally
published MatRouter v0.9.1 package and contains exactly three cases: MoS2
electronic evidence, LiFePO4 thermodynamic evidence, and Bi2Se3 source-native
topology evidence. It has no LLM benchmark, expert gold, policy verdict,
weighted score, or additional material case.

## Common research questions

- **RQ1:** Within the declared catalog, configuration, scope, and budgets, does
  one all-qualified aggregate attempt every capability-matched route and
  preserve each typed outcome and `RecordCompleteness`?
- **RQ2:** What material-data landscape does the cross-source aggregate provide
  for the case—sources, data categories, scientific contexts, specialist data,
  and explicit gaps—and how does that landscape guide the next research step?
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

## Frozen acquisition

Each case calls `aggregate_source_records` exactly once with one
`source_record + all_qualified + exhaust_upstream` requirement. MatRouter v0.9.1
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

RQ2 is reported as a deterministic source-contribution map and case-task trace.
For every exact record source actually present, it identifies the provider
group, contributing data categories and properties, a stable-order
representative record, scientific context, route outcome, and completeness.
Case claims name their supporting source contributions. The trace does not use
a single-source baseline, completeness score, field count, or scientific-truth
judgment. Bundle identity, provenance, and context remain validation and
attribution mechanisms rather than standalone scientific results.

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

- `experiment.py`: the only run, validate, smoke, replay, refresh, and verify
  interface.
- `cases/`: three case specs and scientific boundaries.
- `raw/0.9.1/`: immutable release-bound captures.
- `results/`: derived case capsules, material-landscape case traces, direct
  analysis CSV/JSON/SVG files, product blockers, and the internal protocol
  review.
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
