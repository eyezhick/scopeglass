import json
from dataclasses import replace

import pytest

from scopeglass.cli import main
from scopeglass.materials import material_hash, write_csv, write_jsonl
from scopeglass.stimuli import generate


@pytest.mark.parametrize("suffix,writer", [("jsonl", write_jsonl), ("csv", write_csv)])
def test_custom_materials_are_scored_without_reverting_to_builtins(tmp_path, suffix, writer):
    rows = [replace(row, context="Yesterday, " + row.context)
            for row in generate("np_s")[:4]]
    source = tmp_path / ("custom." + suffix)
    writer(rows, source)
    output = tmp_path / "run"
    main(["run", "--materials", str(source), "--out", str(output), "--bootstrap", "10"])
    result = json.loads((output / "results.json").read_text())
    assert len(result["rows"]) == 4
    assert result["metadata"]["stimuli_sha256"] == material_hash(rows)
    assert all(row["context"].startswith("Yesterday,") for row in result["rows"])


def test_invalid_materials_fail_before_model_loading(tmp_path, monkeypatch):
    source = tmp_path / "broken.jsonl"
    source.write_text('{}\n')
    monkeypatch.setattr("scopeglass.cli.HuggingFaceScorer",
                        lambda *args: pytest.fail("Model must not load for invalid materials"))
    with pytest.raises(SystemExit) as error:
        main(["run", "--backend", "hf", "--materials", str(source)])
    assert error.value.code == 2


def test_cli_material_export_and_validation_roundtrip(tmp_path, capsys):
    source = tmp_path / "materials.csv"
    main(["stimuli", "--experiment", "np_s", "--out", str(source)])
    main(["validate", str(source)])
    description = json.loads(capsys.readouterr().out)
    assert description["n_items"] == 12
    assert description["n_stimuli"] == 48
    assert list(description["experiments"]) == ["np_s"]
