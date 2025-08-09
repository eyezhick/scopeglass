from dataclasses import replace

import pytest

from scopeglass import analysis
from scopeglass.materials import validate_materials
from scopeglass.stimuli import generate


def test_builtin_materials_pass_validation():
    assert validate_materials(generate()) is None


@pytest.mark.parametrize("rows", [[], None, {}, [None]])
def test_validation_rejects_invalid_collections(rows):
    with pytest.raises(ValueError):
        validate_materials(rows)


@pytest.mark.parametrize("field", ["id", "item", "experiment", "context", "target", "spillover"])
def test_validation_rejects_nonstring_text(field):
    rows = generate("garden_path")
    rows[0] = replace(rows[0], **{field: 42})
    with pytest.raises(ValueError, match=f"{field} must be a string"):
        validate_materials(rows)


@pytest.mark.parametrize("field", ["id", "item", "experiment", "context", "target"])
def test_validation_rejects_blank_required_text(field):
    rows = generate("garden_path")
    rows[0] = replace(rows[0], **{field: "  "})
    with pytest.raises(ValueError, match=f"{field} must not be blank"):
        validate_materials(rows)


def test_validation_preserves_unicode_spacing_and_empty_spillover():
    rows = generate("garden_path")
    rows[0] = replace(rows[0], context="The café owner", target="  smiled", spillover="")
    validate_materials(rows)
    assert rows[0].context == "The café owner"
    assert rows[0].target == "  smiled"


@pytest.mark.parametrize("factors", [None, [], {}, {"extra": "value"}])
def test_validation_rejects_wrong_factor_schema(factors):
    rows = generate("garden_path")
    rows[0] = replace(rows[0], factors=factors)
    with pytest.raises(ValueError, match="Unexpected factors"):
        validate_materials(rows)


@pytest.mark.parametrize("level", [True, 1, [], "period"])
def test_validation_rejects_unknown_or_nonstring_factor_levels(level):
    rows = generate("garden_path")
    rows[0] = replace(rows[0], factors={"ambiguity": "ambiguous", "boundary": level})
    with pytest.raises(ValueError, match="Invalid level for boundary"):
        validate_materials(rows)


def test_validation_rejects_unknown_experiment():
    rows = generate("garden_path")
    rows[0] = replace(rows[0], experiment="unregistered")
    with pytest.raises(ValueError, match="Unknown experiment"):
        validate_materials(rows)


def test_validation_uses_registered_designs(monkeypatch):
    monkeypatch.setitem(analysis.DESIGNS, "custom", (("condition",), (("left", "right"),)))
    base = generate("garden_path")[0]
    rows = [
        replace(base, id=f"custom-{level}", experiment="custom", factors={"condition": level})
        for level in ("left", "right")
    ]
    validate_materials(rows)


def test_validation_rejects_reused_stimulus_ids():
    rows = generate("garden_path")
    rows[1] = replace(rows[1], id=rows[0].id)
    with pytest.raises(ValueError, match="Duplicate stimulus id"):
        validate_materials(rows)


def test_validation_rejects_duplicate_cells_with_distinct_ids():
    rows = generate("garden_path")
    rows.append(replace(rows[0], id="another-id"))
    with pytest.raises(ValueError, match="Duplicate cell"):
        validate_materials(rows)


def test_validation_allows_repeated_surface_controls():
    rows = generate("polarity")
    assert len({(row.context, row.target, row.spillover) for row in rows}) < len(rows)
    validate_materials(rows)


@pytest.mark.parametrize("experiment", ["garden_path", "agreement", "polarity"])
def test_validation_rejects_missing_cells(experiment):
    rows = generate(experiment)
    with pytest.raises(ValueError, match="Incomplete factorial design.*missing"):
        validate_materials(rows[1:])


def test_frame_identity_includes_experiment():
    rows = generate("garden_path")[:4] + generate("agreement")[:8]
    rows = [replace(row, item="shared-name") for row in rows]
    validate_materials(rows)


def test_validation_does_not_reorder_materials():
    rows = list(reversed(generate("garden_path")[:8]))
    original_ids = [row.id for row in rows]
    validate_materials(rows)
    assert [row.id for row in rows] == original_ids
