"""Descriptive frame checks, not a rule for excluding inconvenient items."""

from .analysis import analyze
from .compare import validate_run


def item_diagnostics(run: dict) -> list[dict]:
    """Rank each contrast's lexical frames by descending absolute effect."""
    validate_run(run)
    rows = []
    for result in analyze(run["rows"], samples=1):
        ranked = sorted(result["items"], key=lambda item: (-abs(item["value"]), item["item"]))
        for rank, item in enumerate(ranked, 1):
            rows.append({
                "key": result["key"], "title": result["title"],
                "item": item["item"], "value": item["value"],
                "mean": result["estimate"], "deviation": item["value"] - result["estimate"],
                "absolute_rank": rank,
            })
    return rows
