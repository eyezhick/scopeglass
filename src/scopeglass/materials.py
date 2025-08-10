"""Import, inspect, and select complete factorial stimulus sets."""

import json
from collections import defaultdict
from itertools import product
from pathlib import Path

from . import analysis
from .stimuli import Stimulus


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
