from collections import Counter, OrderedDict
from typing import Any, Dict

import jiwer

from suber.metrics.statistics_utilities import format_top_counts


class WERStatisticsCollector:
    """
    Collects word-level edit operation counts from a jiwer.process_words() result, to explain a WER score in more
    detail than the aggregate number: total hits/substitutions/deletions/insertions, as well as the most frequent
    individual word insertions, deletions and substitutions.
    """

    def __init__(self, top_n: int = 10):
        self._top_n = top_n

        self._hits = 0
        self._substitutions = 0
        self._deletions = 0
        self._insertions = 0

        self._substitution_counts = Counter()  # (reference word, hypothesis word) -> count
        self._insertion_counts = Counter()  # hypothesis word -> count
        self._deletion_counts = Counter()  # reference word -> count

        self._alignment_visualization = None

    def add_data(self, output: "jiwer.process.WordOutput"):
        self._hits += output.hits
        self._substitutions += output.substitutions
        self._deletions += output.deletions
        self._insertions += output.insertions

        substitution_counts, insertion_counts, deletion_counts = _collect_word_level_error_counts(output)
        self._substitution_counts.update(substitution_counts)
        self._insertion_counts.update(insertion_counts)
        self._deletion_counts.update(deletion_counts)

        self._alignment_visualization = jiwer.visualize_alignment(output)

    def get_statistics(self) -> Dict[str, Any]:
        return OrderedDict(
            hits=self._hits,
            substitutions=self._substitutions,
            deletions=self._deletions,
            insertions=self._insertions,
            most_common_substitutions=format_top_counts(self._substitution_counts, self._top_n),
            most_common_insertions=format_top_counts(self._insertion_counts, self._top_n),
            most_common_deletions=format_top_counts(self._deletion_counts, self._top_n),
        )

    def get_alignment_visualization(self) -> str:
        """
        Returns a human-readable REF/HYP alignment per segment, as produced by jiwer.visualize_alignment(). Meant to
        be printed separately from the JSON output (e.g. to stderr), not included in it.
        """
        return self._alignment_visualization or ""


def _collect_word_level_error_counts(output: "jiwer.process.WordOutput"):
    """
    Like jiwer.collect_error_counts(), but counts one entry per word instead of joining adjacent
    inserted/deleted/substituted words of the same alignment chunk into a single multi-word phrase.
    Within a "substitute" chunk the reference and hypothesis word ranges are always the same length (any extra
    inserted/deleted words get their own "insert"/"delete" chunk), so zipping them word-by-word is safe.
    """
    substitution_counts = Counter()
    insertion_counts = Counter()
    deletion_counts = Counter()

    for sentence_index, chunks in enumerate(output.alignments):
        ref_words = output.references[sentence_index]
        hyp_words = output.hypotheses[sentence_index]

        for chunk in chunks:
            if chunk.type == "insert":
                for hyp_word in hyp_words[chunk.hyp_start_idx:chunk.hyp_end_idx]:
                    insertion_counts[hyp_word] += 1
            elif chunk.type == "delete":
                for ref_word in ref_words[chunk.ref_start_idx:chunk.ref_end_idx]:
                    deletion_counts[ref_word] += 1
            elif chunk.type == "substitute":
                ref_chunk_words = ref_words[chunk.ref_start_idx:chunk.ref_end_idx]
                hyp_chunk_words = hyp_words[chunk.hyp_start_idx:chunk.hyp_end_idx]
                for ref_word, hyp_word in zip(ref_chunk_words, hyp_chunk_words):
                    substitution_counts[(ref_word, hyp_word)] += 1

    return substitution_counts, insertion_counts, deletion_counts
