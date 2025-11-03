"""Descriptive frame checks, not a rule for excluding inconvenient items."""

from statistics import mean

from .analysis import analyze
from .compare import validate_run


def item_diagnostics(run: dict) -> list[dict]:
    """Rank each contrast's lexical frames by descending absolute effect."""
    validate_run(run)
    rows = []
    for result in analyze(run["rows"], samples=1):
        ranked = sorted(result["items"], key=lambda item: (-abs(item["value"]), item["item"]))
        for rank, item in enumerate(ranked, 1):
            remaining = [other["value"] for other in ranked if other["item"] != item["item"]]
            leave_one_out = mean(remaining) if remaining else None
            rows.append({
                "key": result["key"], "title": result["title"],
                "item": item["item"], "value": item["value"],
                "mean": result["estimate"], "deviation": item["value"] - result["estimate"],
                "absolute_rank": rank, "leave_one_out": leave_one_out,
                "mean_shift": (leave_one_out - result["estimate"]
                               if leave_one_out is not None else None),
            })
    return rows
