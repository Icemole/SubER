from collections import Counter, OrderedDict
from typing import Any, Dict, List


def format_top_counts(counter: Counter, top_n: int) -> List[Dict[str, Any]]:
    """
    Turns a Counter into a list of dicts sorted by descending count, for JSON-friendly output. Keys that are tuples
    (reference, hypothesis) are treated as substitutions, plain keys as insertions/deletions of a single word.
    """
    formatted = []
    for key, count in counter.most_common(top_n):
        if isinstance(key, tuple):
            reference, hypothesis = key
            formatted.append(OrderedDict(reference=reference, hypothesis=hypothesis, count=count))
        else:
            formatted.append(OrderedDict(word=key, count=count))
    return formatted
