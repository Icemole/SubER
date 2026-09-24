from collections import OrderedDict
from typing import Any, Dict

import jiwer


class WERStatisticsCollector:
    """
    Collects word-level edit operation counts from a jiwer.process_words() result, to explain a WER score in more
    detail than the aggregate number.
    """

    def __init__(self):
        self._hits = 0
        self._substitutions = 0
        self._deletions = 0
        self._insertions = 0

    def add_data(self, output: "jiwer.process.WordOutput"):
        self._hits += output.hits
        self._substitutions += output.substitutions
        self._deletions += output.deletions
        self._insertions += output.insertions

    def get_statistics(self) -> Dict[str, Any]:
        return OrderedDict(
            hits=self._hits,
            substitutions=self._substitutions,
            deletions=self._deletions,
            insertions=self._insertions,
        )
