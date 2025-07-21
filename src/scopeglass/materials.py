"""Import, inspect, and select complete factorial stimulus sets."""

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
