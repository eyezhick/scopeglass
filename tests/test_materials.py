import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scopeglass import analysis
from scopeglass.materials import (
    describe_materials,
    load_csv,
    load_jsonl,
    material_hash,
    select_items,
    validate_materials,
    write_csv,
    write_jsonl,
)
from scopeglass.stimuli import Stimulus, generate


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


def test_item_selection_preserves_source_order_and_all_cells():
    rows = generate("garden_path")
    selected = select_items(rows, ["npz-03", "npz-01"])
    assert selected == rows[4:8] + rows[12:16]
    validate_materials(selected)
    assert len(rows) == 48


def test_default_selection_returns_a_new_list():
    rows = generate("garden_path")[:4]
    selected = select_items(rows)
    assert selected == rows
    assert selected is not rows


@pytest.mark.parametrize("items", [[], "npz-00", [None], [3], [" "]])
def test_item_selection_rejects_malformed_requests(items):
    with pytest.raises(ValueError, match="nonempty list of item ids"):
        select_items(generate("garden_path"), items)


def test_item_selection_names_unknown_ids():
    with pytest.raises(ValueError, match="Unknown item ids: a-missing, z-missing"):
        select_items(generate(), ["z-missing", "npz-00", "a-missing"])


def test_item_selection_does_not_duplicate_frames():
    rows = generate("garden_path")
    assert select_items(rows, ["npz-00", "npz-00"]) == rows[:4]


def test_item_selection_includes_same_named_items_from_each_experiment():
    rows = generate("garden_path")[:4] + generate("agreement")[:8]
    rows = [replace(row, item="shared") for row in rows]
    assert select_items(rows, ["shared"]) == rows


@pytest.mark.parametrize("limit", [0, -1, True, False, 1.0, "1"])
def test_item_limits_require_positive_integers(limit):
    with pytest.raises(ValueError, match="positive integer"):
        select_items(generate(), limit=limit)


def test_item_limit_keeps_complete_interleaved_frames():
    rows = generate("garden_path")[:8]
    interleaved = [row for pair in zip(rows[:4], rows[4:]) for row in pair]
    assert select_items(interleaved, limit=1) == rows[:4]


def test_item_limit_applies_after_explicit_selection():
    rows = generate("garden_path")
    assert select_items(rows, ["npz-02", "npz-01"], limit=1) == rows[4:8]


def test_item_limit_counts_frames_from_different_experiments():
    rows = generate("garden_path")[:4] + generate("agreement")[:8]
    rows = [replace(row, item="shared") for row in rows]
    assert select_items(rows, limit=1) == rows[:4]
    assert select_items(rows, limit=2) == rows
    assert select_items(rows, limit=100) == rows


def test_limit_does_not_hide_unknown_requested_items():
    with pytest.raises(ValueError, match="Unknown item ids"):
        select_items(generate(), ["npz-00", "does-not-exist"], limit=1)


def test_material_hash_matches_archived_run_metadata():
    path = Path(__file__).parents[1] / "examples" / "distilgpt2" / "results.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    rows = [Stimulus(**{key: row[key] for key in Stimulus.__dataclass_fields__})
            for row in run["rows"]]
    assert material_hash(rows) == run["metadata"]["stimuli_sha256"]


def test_material_hash_tracks_text_and_presentation_order():
    rows = generate("garden_path")[:4]
    changed = [replace(rows[0], target=rows[0].target + " away"), *rows[1:]]
    assert material_hash(rows) != material_hash(changed)
    assert material_hash(rows) != material_hash(list(reversed(rows)))


def test_material_hash_ignores_factor_key_order():
    rows = generate("garden_path")[:4]
    reordered = [replace(row, factors=dict(reversed(list(row.factors.items())))) for row in rows]
    assert material_hash(rows) == material_hash(reordered)


def test_invalid_materials_cannot_receive_a_validity_hash():
    with pytest.raises(ValueError, match="Incomplete factorial design"):
        material_hash(generate("garden_path")[:3])


def test_description_reports_balanced_counts_and_factor_levels():
    rows = generate("garden_path")[:8] + generate("agreement")[:8]
    description = describe_materials(rows)
    assert description["n_stimuli"] == 16
    assert description["n_items"] == 3
    assert list(description["experiments"]) == ["garden_path", "agreement"]
    assert description["experiments"]["garden_path"] == {
        "n_stimuli": 8,
        "n_items": 2,
        "factors": {"ambiguity": ["ambiguous", "control"], "boundary": ["absent", "comma"]},
    }
    assert description["experiments"]["agreement"]["n_items"] == 1
    assert description["material_hash"] == material_hash(rows)
    assert json.loads(json.dumps(description)) == description


def test_description_counts_same_named_frames_separately():
    rows = generate("garden_path")[:4] + generate("agreement")[:8]
    rows = [replace(row, item="shared") for row in rows]
    assert describe_materials(rows)["n_items"] == 2


def test_description_does_not_expose_mutable_design_levels():
    rows = generate("garden_path")[:4]
    description = describe_materials(rows)
    description["experiments"]["garden_path"]["factors"]["boundary"].append("period")
    assert "period" not in describe_materials(rows)["experiments"]["garden_path"]["factors"][
        "boundary"
    ]


def test_description_rejects_invalid_materials():
    with pytest.raises(ValueError, match="nonempty"):
        describe_materials([])


@pytest.mark.parametrize("key,replacement", [
    ("id", '"id": "overwritten", "id":'),
    ("boundary", '"boundary": "comma", "boundary":'),
])
def test_jsonl_rejects_silently_overwritten_record_and_factor_keys(tmp_path, key, replacement):
    rows = generate("garden_path")[:4]
    lines = [json.dumps(row.to_dict()) for row in rows]
    lines[0] = lines[0].replace(f'"{key}":', replacement, 1)
    path = tmp_path / "duplicate.jsonl"
    path.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match=f"duplicate.jsonl:1: Duplicate JSON key: {key}"):
        load_jsonl(path)


def test_csv_round_trip_preserves_unicode_multiline_text_and_empty_spillover(tmp_path):
    rows = generate()
    rows[0] = replace(rows[0], context='The café owner said, "hello"\nthen', spillover="")
    path = tmp_path / "materials.csv"
    write_csv(rows, path)
    assert load_csv(path) == rows


@pytest.mark.parametrize("header", [
    "",
    "id,item,experiment,context,target,spillover",
    "id,id,experiment,context,target,spillover,factors",
    "id,item,experiment,context,target,spillover,factors,score",
])
def test_csv_rejects_missing_duplicate_or_extra_headers(tmp_path, header):
    path = tmp_path / "bad-header.csv"
    path.write_text(header + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV header must contain exactly"):
        load_csv(path)


@pytest.mark.parametrize("record", ["a,b", "a,b,c,d,e,f,g,h"])
def test_csv_rejects_wrong_column_counts_with_line_numbers(tmp_path, record):
    path = tmp_path / "bad-row.csv"
    path.write_text(
        "id,item,experiment,context,target,spillover,factors\n" + record, encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bad-row.csv:2: CSV row"):
        load_csv(path)


def test_csv_rejects_duplicated_factor_keys(tmp_path):
    path = tmp_path / "duplicate.csv"
    record = generate()[0].to_dict()
    record["factors"] = '{"boundary":"absent","boundary":"comma","ambiguity":"ambiguous"}'
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=record)
        writer.writeheader()
        writer.writerow(record)
    with pytest.raises(ValueError, match="duplicate.csv:2: Duplicate JSON key: boundary"):
        load_csv(path)


def test_csv_accepts_reordered_headers_and_utf8_bom(tmp_path):
    rows = generate("garden_path")[:4]
    path = tmp_path / "reordered.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(reversed(rows[0].to_dict())))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict() | {"factors": json.dumps(row.factors)})
    assert load_csv(path) == rows


def test_csv_rejects_unclosed_quoted_fields(tmp_path):
    path = tmp_path / "unclosed.csv"
    path.write_text(
        'id,item,experiment,context,target,spillover,factors\n"unclosed', encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unclosed.csv:.*unexpected end of data"):
        load_csv(path)


def test_csv_validates_complete_frames_after_import(tmp_path):
    path = tmp_path / "incomplete.csv"
    write_csv(generate("garden_path")[:4], path)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete.csv: Incomplete factorial design"):
        load_csv(path)
