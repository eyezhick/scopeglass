"""Import, inspect, and select complete factorial stimulus sets."""

from . import analysis
from .stimuli import Stimulus


def validate_materials(rows: list[Stimulus]) -> None:
    """Reject malformed stimulus records without normalizing their text."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("Materials must be a nonempty list of Stimulus records")
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
