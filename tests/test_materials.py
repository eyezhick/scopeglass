import csv
import json
from dataclasses import replace

import pytest

from scopeglass import analysis
from scopeglass.materials import load_jsonl, validate_materials, write_csv, write_jsonl
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


def test_jsonl_export_preserves_all_fields_and_unicode(tmp_path):
    rows = generate("garden_path")[:4]
    rows[0] = replace(rows[0], context="The café owner", target="  smiled", spillover="")
    path = tmp_path / "materials.jsonl"
    write_jsonl(rows, path)
    text = path.read_text(encoding="utf-8")
    assert "café" in text
    assert text.endswith("\n")
    assert [json.loads(line) for line in text.splitlines()] == [row.to_dict() for row in rows]


def test_jsonl_export_is_independent_of_factor_insertion_order(tmp_path):
    rows = generate("garden_path")[:4]
    reordered = [replace(row, factors=dict(reversed(list(row.factors.items())))) for row in rows]
    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    write_jsonl(rows, first)
    write_jsonl(reordered, second)
    assert first.read_bytes() == second.read_bytes()


def test_jsonl_export_validates_before_overwriting(tmp_path):
    path = tmp_path / "materials.jsonl"
    path.write_text("existing materials", encoding="utf-8")
    with pytest.raises(ValueError, match="Incomplete factorial design"):
        write_jsonl(generate("garden_path")[:3], path)
    assert path.read_text(encoding="utf-8") == "existing materials"


def test_jsonl_round_trip_reconstructs_stimulus_records(tmp_path):
    rows = generate()
    path = tmp_path / "materials.jsonl"
    write_jsonl(rows, path)
    assert load_jsonl(path) == rows


@pytest.mark.parametrize("record", [None, [], "sentence", {"id": "missing-fields"}])
def test_jsonl_rejects_nonrecords_and_missing_fields(tmp_path, record):
    path = tmp_path / "materials.jsonl"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="Each record must contain exactly"):
        load_jsonl(path)


def test_jsonl_rejects_unexpected_fields(tmp_path):
    record = generate()[0].to_dict() | {"surprisal_bits": 2.0}
    path = tmp_path / "materials.jsonl"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="Each record must contain exactly"):
        load_jsonl(path)


def test_jsonl_skips_blank_lines_but_rejects_empty_materials(tmp_path):
    rows = generate("garden_path")[:4]
    path = tmp_path / "materials.jsonl"
    path.write_text("\n\n".join(json.dumps(row.to_dict()) for row in rows), encoding="utf-8")
    assert load_jsonl(path) == rows
    path.write_text("\n \n", encoding="utf-8")
    with pytest.raises(ValueError, match="nonempty"):
        load_jsonl(path)


def test_jsonl_rejects_incomplete_imported_frames(tmp_path):
    path = tmp_path / "materials.jsonl"
    path.write_text(json.dumps(generate()[0].to_dict()), encoding="utf-8")
    with pytest.raises(ValueError, match="Incomplete factorial design"):
        load_jsonl(path)


@pytest.mark.parametrize("bad_line", ['{"broken":', '{"id": "only-one-field"}'])
def test_jsonl_parse_errors_name_the_file_and_physical_line(tmp_path, bad_line):
    path = tmp_path / "broken.jsonl"
    path.write_text("\n\n" + bad_line, encoding="utf-8")
    with pytest.raises(ValueError, match="broken.jsonl:3:"):
        load_jsonl(path)


def test_jsonl_design_errors_name_the_input_file(tmp_path):
    rows = generate("garden_path")[:4]
    rows[0] = replace(rows[0], target=None)
    path = tmp_path / "wrong-type.jsonl"
    path.write_text("\n".join(json.dumps(row.to_dict()) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="wrong-type.jsonl: Row 1: target must be a string"):
        load_jsonl(path)


def test_jsonl_accepts_utf8_bom_from_text_editors(tmp_path):
    rows = generate("garden_path")[:4]
    path = tmp_path / "bom.jsonl"
    path.write_text("\n".join(json.dumps(row.to_dict()) for row in rows), encoding="utf-8-sig")
    assert load_jsonl(path) == rows


def test_csv_export_quotes_text_and_preserves_full_records(tmp_path):
    rows = generate("garden_path")[:4]
    rows[0] = replace(rows[0], context='The café owner said, "hello"\nthen', spillover="")
    path = tmp_path / "materials.csv"
    write_csv(rows, path)
    with path.open(encoding="utf-8", newline="") as source:
        records = list(csv.DictReader(source))
    for record in records:
        record["factors"] = json.loads(record["factors"])
    assert records == [row.to_dict() for row in rows]


def test_csv_export_is_independent_of_factor_insertion_order(tmp_path):
    rows = generate("garden_path")[:4]
    reordered = [replace(row, factors=dict(reversed(list(row.factors.items())))) for row in rows]
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    write_csv(rows, first)
    write_csv(reordered, second)
    assert first.read_bytes() == second.read_bytes()


def test_csv_export_validates_before_overwriting(tmp_path):
    path = tmp_path / "materials.csv"
    path.write_text("existing materials", encoding="utf-8")
    with pytest.raises(ValueError, match="Incomplete factorial design"):
        write_csv(generate("garden_path")[:3], path)
    assert path.read_text(encoding="utf-8") == "existing materials"
