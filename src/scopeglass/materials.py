"""Import, inspect, and select complete factorial stimulus sets."""

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import fields
from itertools import product
from pathlib import Path

from . import analysis
from .stimuli import Stimulus

_FIELDS = tuple(field.name for field in fields(Stimulus))


def validate_materials(rows: list[Stimulus]) -> None:
    """Require unique records and complete frames without normalizing text."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("Materials must be a nonempty list of Stimulus records")
    seen_ids = set()
    cells = defaultdict(set)
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Stimulus):
            raise ValueError(f"Row {index} must be a Stimulus record")
        for field in ("id", "item", "experiment", "context", "target", "spillover"):
            value = getattr(row, field)
            if not isinstance(value, str):
                raise ValueError(f"Row {index}: {field} must be a string")
            if field != "spillover" and not value.strip():
                raise ValueError(f"Row {index}: {field} must not be blank")
        if row.experiment not in analysis.DESIGNS:
            raise ValueError(f"Unknown experiment: {row.experiment}")
        fields, levels = analysis.DESIGNS[row.experiment]
        if not isinstance(row.factors, dict) or set(row.factors) != set(fields):
            raise ValueError(f"Unexpected factors in {row.id}; expected {', '.join(fields)}")
        for name, allowed in zip(fields, levels):
            value = row.factors[name]
            if not isinstance(value, str) or value not in allowed:
                raise ValueError(f"Invalid level for {name} in {row.id}: {value!r}")
        if row.id in seen_ids:
            raise ValueError(f"Duplicate stimulus id: {row.id}")
        seen_ids.add(row.id)
        cell = tuple(row.factors[name] for name in fields)
        frame = cells[row.experiment, row.item]
        if cell in frame:
            raise ValueError(f"Duplicate cell in {row.experiment}/{row.item}: {cell}")
        frame.add(cell)
    for (experiment, item), observed in cells.items():
        expected = set(product(*analysis.DESIGNS[experiment][1]))
        if observed != expected:
            raise ValueError(
                f"Incomplete factorial design for {experiment}/{item}: "
                f"missing {sorted(expected - observed)}"
            )


def write_jsonl(rows: list[Stimulus], path: Path) -> None:
    """Write validated UTF-8 records, with sorted keys and one record per line."""
    validate_materials(rows)
    content = "".join(json.dumps(row.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
                      for row in rows)
    Path(path).write_text(content, encoding="utf-8")


def load_jsonl(path: Path) -> list[Stimulus]:
    """Read full stimulus records and validate the complete imported design."""
    rows = []
    with Path(path).open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or set(record) != set(_FIELDS):
                    raise ValueError(f"Each record must contain exactly: {', '.join(_FIELDS)}")
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            rows.append(Stimulus(**record))
    try:
        validate_materials(rows)
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error
    return rows


def write_csv(rows: list[Stimulus], path: Path) -> None:
    """Write every stimulus field; factors occupy one sorted JSON column."""
    validate_materials(rows)
    with Path(path).open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            record = row.to_dict()
            record["factors"] = json.dumps(row.factors, ensure_ascii=False, sort_keys=True)
            writer.writerow(record)


def select_items(
    rows: list[Stimulus], items: list[str] | None = None, limit: int | None = None,
) -> list[Stimulus]:
    """Select complete frames in source order; limit counts (experiment, item) pairs."""
    validate_materials(rows)
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
    ):
        raise ValueError("Item limit must be a positive integer")
    available = {row.item for row in rows}
    if items is None:
        wanted = available
    else:
        if not isinstance(items, list) or not items or any(
            not isinstance(item, str) or not item.strip() for item in items
        ):
            raise ValueError("Items must be a nonempty list of item ids")
        wanted = set(items)
        unknown = wanted - available
        if unknown:
            raise ValueError(f"Unknown item ids: {', '.join(sorted(unknown))}")
    selected = [row for row in rows if row.item in wanted]
    if limit is not None:
        frames = list(dict.fromkeys((row.experiment, row.item) for row in selected))
        retained = set(frames[:limit])
        selected = [row for row in selected if (row.experiment, row.item) in retained]
    return selected


def material_hash(rows: list[Stimulus]) -> str:
    """Hash validated records using the same serialization as run metadata."""
    validate_materials(rows)
    content = json.dumps([row.to_dict() for row in rows], sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()


def describe_materials(rows: list[Stimulus]) -> dict:
    """Summarize validated row counts, frame counts, and registered factor levels."""
    fingerprint = material_hash(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row.experiment].append(row)
    experiments = {}
    for experiment, records in groups.items():
        names, levels = analysis.DESIGNS[experiment]
        experiments[experiment] = {
            "n_stimuli": len(records),
            "n_items": len({row.item for row in records}),
            "factors": {name: list(allowed) for name, allowed in zip(names, levels)},
        }
    return {
        "n_stimuli": len(rows),
        "n_items": sum(group["n_items"] for group in experiments.values()),
        "experiments": experiments,
        "material_hash": fingerprint,
    }
