# Localized dataset generation uses indexed sequential processing

## Context

Localized dataset generation reads a large `d4data` checkout to produce D4LF's JSON assets. The
affix stage was the dominant cost because it parsed every Power JSON file only to build a mapping
from power SNO identifiers to power names. The generator also had coarse progress output that
described the affix stage as slow without measuring it.

Experiments used the same `enUS` checkout and verified generated-file SHA-256 hashes after every
run. Per-file thread pools and overlapping the independent top-level stages were both slower on
the target Windows workstation because the workload is dominated by local file I/O and parsing
overhead.

## Decision

- Use section `29` of `CoreTOC.dat.json` as the power SNO-to-name index when it is present.
- Fall back to scanning Power JSON files when that index is unavailable.
- Keep dataset stages and per-file processing sequential. Do not ship worker-count or
  auto-tuning controls based on the benchmark experiments.
- Print low-volume `START`/`FINISH` stage messages with source-file counts and elapsed time.
- Cache localized power-name projections for the duration of one generation run.
- Preserve deterministic traversal, JSON serialization, output ordering, and existing failure
  behavior.

## Evidence

On 2026-07-23, the indexed sequential implementation completed the full run in approximately
0.80 seconds on three warm in-process runs, versus approximately 1.88 seconds before the index
change. The affix stage decreased from approximately 1.48 seconds to 0.56 seconds. After the
index change, worker-count experiments averaged approximately 0.80 seconds with one worker,
1.08 seconds with two or four, 1.09 seconds with eight, and 1.12 seconds with sixteen. All
generated-file hashes matched the baseline.

## Consequences

Generation avoids parsing thousands of Power files on current `d4data` checkouts and reports
where future time is spent. The fallback retains behavior for source checkouts without the
CoreTOC index. Parallel execution remains a rejected optimization for this workload; it can be
reconsidered if the source format or hardware changes, using the stage timings and output hashes
as the regression guard.
