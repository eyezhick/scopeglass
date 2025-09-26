"""Compare saved scores on identical lexical frames."""


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
    if not isinstance(run.get("rows"), list) or not run["rows"]:
        raise ValueError("Run rows must be a nonempty list")
