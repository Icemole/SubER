# Verbose / Diagnostic Output — Implementation Plan

Status: Tier 1 items 1–3 implemented on 2026-09-24 (see commits touching `wer_statistics.py`,
`suber_statistics.py`, `statistics_utilities.py`). Items 4, and Tiers 2–3, are still just planned.

## Goal

Let SubER report *why* a score is what it is, not just the number:

- WER insertions / deletions / substitutions
- Most common error sources (top insertions / deletions / substitutions)
- Timing shifts of subtitle boxes
- Subtitle box insertion / deletion / merge / split
- Line division (`<eol>` / `<eob>`) errors

## Current state

- `--suber-statistics` adds an `#info` block with **aggregate** SubER counts
  (`suber/metrics/suber_statistics.py`): word/break insertions, deletions, substitutions, `num_shifts`,
  number of reference words and breaks.
- WER (`suber/metrics/jiwer_interface.py`) only calls `jiwer.wer()` and returns a float.
- Nothing is reported per edit, nothing ranks errors by frequency, and box-level events are not classified.

The tiers below are ordered from least to most effort.

## Tier 1 — Expose data that is already computed (< 1h each)

1. **DONE. WER breakdown.** `suber/metrics/jiwer_interface.py` now calls `jiwer.process_words()` instead of
   `jiwer.wer()` whenever a `WERStatisticsCollector` is passed in (`suber/metrics/wer_statistics.py`); the score
   itself is unchanged either way. `--wer-statistics` reports `hits`/`substitutions`/`deletions`/`insertions` in
   `#info` for `WER`, `WER-cased`, `AS-WER`, `t-WER` and the `-seg` variants.
2. **DONE. Top WER errors.** `WERStatisticsCollector` also reports `most_common_substitutions` /
   `most_common_insertions` / `most_common_deletions` (via `jiwer.collect_error_counts`, top-N controlled by the
   new `--top-n` flag, shared with `--suber-statistics`). Note: `jiwer.collect_error_counts` groups adjacent
   substituted/inserted/deleted words into a single multi-word phrase, so e.g. two consecutive substitutions can
   show up as one entry. `jiwer.visualize_alignment()` output (REF/HYP per segment) is printed to stderr, not
   included in the JSON on stdout.
3. **DONE. SubER per-edit list.** `SubERStatisticsCollector.add_data` (`suber/metrics/suber_statistics.py`) now
   records each edit into a `Counter` in addition to the aggregate counts, exposed as `most_common_word_*` /
   `most_common_break_*` in `#info`. Break edits are keyed by the actual symbol (`<eol>`/`<eob>`), so e.g. a line
   break replaced by a block break is a distinct entry from the reverse. Per-instance timestamps were **not**
   implemented (out of scope for this pass — would need a raw edit log, not just top-N counts).
4. **Not implemented. `num_shifts` per part.** `calculate_SubER` already processes independent time chunks
   (`_get_independent_parts` in `suber/metrics/suber.py`). Record shift counts per chunk with its time range.

A shared `format_top_counts()` helper lives in `suber/metrics/statistics_utilities.py`, used by both collectors.

## Tier 2 — Small algorithm plumbing (~half a day)

5. **Per-shift details.** `_shift()` in `suber/metrics/lib_ter.py` chooses `start_h`, `length` and a target index
   but returns only the shifted word list. Return the chosen move as well and log it in the shift loop in
   `translation_edit_rate()` (which words moved, and between which timestamps). This touches core metric code,
   so add tests asserting scores are unchanged.
6. **Per-box timing drift.** Independent of TER: pair hypothesis and reference boxes (via
   `time_align_hypothesis_to_reference` or SubER word matches) and report start/end time deltas
   (mean, max, histogram).

## Tier 3 — New analysis (1–2+ days)

7. **Box insertion / deletion / merge / split classification.** SubER flattens subtitles into one stream of
   words and break tokens, so a merge is never a single event. Build a time-overlap mapping between hypothesis
   and reference `Subtitle` objects:

   | Reference boxes | Hypothesis boxes | Event |
   |---|---|---|
   | 1 | 0 | deletion |
   | 0 | 1 | insertion |
   | 1 | N | split |
   | N | 1 | merge |
   | N | M | re-segmentation |

   Implement as a separate module. The main work is choosing overlap thresholds.

## Output design (all tiers)

- Keep the default JSON output unchanged.
- Put details in `#info` behind a flag: either a single `--verbose`, or `--wer-statistics` next to the existing
  `--suber-statistics`. Add `--top-n` for the error rankings.
- Send human-readable alignments to stderr or to a file via `--details-file`, so scripts parsing stdout JSON
  keep working.
- Extend `tests/test_suber_statistics.py` with each item. Any change to scoring code needs a test showing
  scores are unchanged.
