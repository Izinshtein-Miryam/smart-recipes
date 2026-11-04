"""Set-overlap helpers for recipe similarity."""

from collections.abc import Iterable


def jaccard(a: Iterable[object], b: Iterable[object]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
