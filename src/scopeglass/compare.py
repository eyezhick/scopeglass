"""Compare saved scores on identical lexical frames."""

import math
from copy import deepcopy
from statistics import mean

from .analysis import analyze, bootstrap


def _surprisal(value, field):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite nonnegative surprisal")


def validate_run(run: dict) -> None:
    """Reject malformed saved runs before analyzing or comparing them."""
    if not isinstance(run, dict):
        raise ValueError("Run must be an object")
    if type(run.get("schema_version")) is not int or run["schema_version"] != 1:
        raise ValueError("Run schema_version must be 1")
    metadata = run.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Run metadata must be an object")
    for field in ("backend", "model"):
        if not isinstance(metadata.get(field), str) or not metadata[field]:
            raise ValueError(f"Run metadata.{field} must be a nonempty string")
    if type(metadata.get("empirical")) is not bool:
        raise ValueError("Run metadata.empirical must be a boolean")
    expected_empirical = {"toy": False, "huggingface": True}.get(metadata["backend"])
    if expected_empirical is not None and metadata["empirical"] != expected_empirical:
        raise ValueError("Run metadata backend contradicts empirical status")
    if not isinstance(run.get("rows"), list) or not run["rows"]:
        raise ValueError("Run rows must be a nonempty list")
    for index, row in enumerate(run["rows"]):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index} must be an object")
        for field in ("id", "item", "experiment", "context", "target", "spillover"):
            if not isinstance(row.get(field), str):
                raise ValueError(f"Row {index}.{field} must be a string")
            if field != "spillover" and not row[field].strip():
                raise ValueError(f"Row {index}.{field} must not be empty")
        factors = row.get("factors")
        if not isinstance(factors, dict) or not factors:
            raise ValueError(f"Row {index}.factors must be a nonempty object")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in factors.items()):
            raise ValueError(f"Row {index}.factors must map strings to strings")
        _surprisal(row.get("surprisal_bits"), f"Row {index}.surprisal_bits")
        tokens = row.get("tokens")
        if not isinstance(tokens, list) or not tokens:
            raise ValueError(f"Row {index}.tokens must be a nonempty list")
        for token in tokens:
            if not isinstance(token, dict) or not isinstance(token.get("text"), str):
                raise ValueError(f"Row {index}.tokens entries require text strings")
            _surprisal(token.get("bits"), f"Row {index}.tokens bits")
            if "id" in token and (type(token["id"]) is not int or token["id"] < 0):
                raise ValueError(f"Row {index}.tokens id must be a nonnegative integer")
        if not math.isclose(sum(t["bits"] for t in tokens), row["surprisal_bits"],
                            rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Row {index}.tokens bits must sum to surprisal_bits")
    # Reuse the registered designs and contrast validation, never a cached summary.
    analyze(run["rows"], samples=1)


MATERIAL_FIELDS = ("id", "item", "experiment", "context", "target", "spillover", "factors")


def _materials(run):
    return {row["id"]: {field: row[field] for field in MATERIAL_FIELDS} for row in run["rows"]}


def compare_runs(left: dict, right: dict, samples=2000, seed=17) -> dict:
    """Recompute contrasts and subtract LEFT from RIGHT on identical materials."""
    if type(samples) is not int or samples < 1:
        raise ValueError("samples must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    validate_run(left)
    validate_run(right)
    if left["metadata"]["empirical"] != right["metadata"]["empirical"]:
        raise ValueError("Cannot compare toy and empirical runs")
    if _materials(left) != _materials(right):
        raise ValueError("Runs must contain identical materials and complete item sets")
    left_results = {result["key"]: result for result in analyze(left["rows"], samples=1)}
    summary = []
    for result in analyze(right["rows"], samples=1):
        baseline = left_results[result["key"]]
        left_items = {item["item"]: item["value"] for item in baseline["items"]}
        items = [{"item": item["item"], "left": left_items[item["item"]],
                  "right": item["value"], "delta": item["value"] - left_items[item["item"]]}
                 for item in result["items"]]
        summary.append({
            "key": result["key"], "title": result["title"],
            "interpretation": "Positive: RIGHT has a larger contrast than LEFT; "
                              "this is not automatically a better model.",
            "contrast_interpretation": result["interpretation"],
            "left_estimate": baseline["estimate"], "right_estimate": result["estimate"],
            "estimate": mean(item["delta"] for item in items),
            "ci95": bootstrap([item["delta"] for item in items], samples=samples, seed=seed),
            "n_items": len(items), "items": items,
        })
    return {"schema_version": 1, "kind": "paired_comparison",
            "direction": "right_minus_left", "analysis": {"samples": samples, "seed": seed},
            "metadata": {"left": deepcopy(left["metadata"]), "right": deepcopy(right["metadata"])},
            "summary": summary}
