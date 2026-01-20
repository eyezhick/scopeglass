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


def test_cli_selection_keeps_every_condition_for_requested_frame(tmp_path):
    main(["run", "--item", "agr-03", "--limit-items", "1", "--out", str(tmp_path),
          "--bootstrap", "10"])
    result = json.loads((tmp_path / "results.json").read_text())
    assert len(result["rows"]) == 8
    assert {row["item"] for row in result["rows"]} == {"agr-03"}
    assert all(result["n_items"] == 1 for result in result["summary"])


def test_unknown_cli_item_fails_without_creating_output(tmp_path):
    output = tmp_path / "run"
    with pytest.raises(SystemExit):
        main(["run", "--item", "missing-item", "--out", str(output)])
    assert not output.exists()


def test_cli_paired_comparison_has_zero_delta_for_identical_runs(tmp_path):
    main(["run", "--item", "nps-00", "--out", str(tmp_path), "--bootstrap", "10"])
    source = str(tmp_path / "results.json")
    output = tmp_path / "comparison.json"
    main(["compare", source, source, "--bootstrap", "10", "--out", str(output)])
    comparison = json.loads(output.read_text())
    assert comparison["direction"] == "right_minus_left"
    assert comparison["summary"][0]["estimate"] == 0
    assert comparison["summary"][0]["ci95"] == [0, 0]


def test_diagnostics_cli_handles_a_single_frame(tmp_path, capsys):
    main(["run", "--item", "nps-00", "--out", str(tmp_path), "--bootstrap", "10"])
    capsys.readouterr()
    main(["diagnose", str(tmp_path / "results.json")])
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["item"] == "nps-00"
    assert rows[0]["leave_one_out"] is None


def test_report_rejects_corrupt_token_scores(tmp_path):
    main(["run", "--item", "nps-00", "--out", str(tmp_path), "--bootstrap", "10"])
    path = tmp_path / "results.json"
    result = json.loads(path.read_text())
    result["rows"][0]["tokens"][0]["bits"] += 1
    path.write_text(json.dumps(result))
    output = tmp_path / "broken.html"
    with pytest.raises(SystemExit):
        main(["report", str(path), "--out", str(output)])
    assert not output.exists()
