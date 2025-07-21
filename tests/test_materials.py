from dataclasses import replace

import pytest

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
