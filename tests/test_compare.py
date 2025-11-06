from copy import deepcopy

import pytest

from scopeglass.analysis import bootstrap
from scopeglass.compare import compare_runs, validate_run
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate


def saved_run(experiment="garden_path"):
    scorer = ToyScorer()
    return {
        "schema_version": 1,
        "metadata": dict(scorer.metadata),
        "rows": [{**row.to_dict(), **scorer.score(row)} for row in generate(experiment)],
    }


def test_valid_saved_run():
    validate_run(saved_run())


@pytest.mark.parametrize("version", [None, True, "1", 2])
def test_rejects_unsupported_schema(version):
    run = saved_run()
    run["schema_version"] = version
    with pytest.raises(ValueError, match="schema_version"):
        validate_run(run)


@pytest.mark.parametrize("field,value", [("empirical", 1), ("backend", ""), ("model", [])])
def test_rejects_invalid_metadata(field, value):
    run = deepcopy(saved_run())
    run["metadata"][field] = value
    with pytest.raises(ValueError, match=f"metadata.{field}"):
        validate_run(run)


@pytest.mark.parametrize("field,value", [
    ("id", ""), ("item", 7), ("context", "  "), ("target", None),
    ("spillover", 1), ("factors", []), ("factors", {"boundary": 1}),
])
def test_validates_stimulus_fields(field, value):
    run = saved_run()
    run["rows"][0][field] = value
    with pytest.raises(ValueError, match=field):
        validate_run(run)


def test_empty_spillover_is_valid():
    run = saved_run()
    run["rows"][0]["spillover"] = ""
    validate_run(run)


@pytest.mark.parametrize("value", [True, "4", None, -1, float("nan"), float("inf")])
def test_surprisal_requires_finite_nonnegative_number(value):
    run = saved_run()
    run["rows"][0]["surprisal_bits"] = value
    with pytest.raises(ValueError, match="surprisal"):
        validate_run(run)


@pytest.mark.parametrize("tokens", [[], [None], [{"text": " x", "bits": True}],
                                     [{"text": " x", "bits": 7, "id": -1}]])
def test_invalid_target_tokens(tokens):
    run = saved_run()
    run["rows"][0]["tokens"] = tokens
    with pytest.raises(ValueError, match="tokens"):
        validate_run(run)


def test_token_bits_must_agree_with_region_total():
    run = saved_run()
    run["rows"][0]["tokens"][0]["bits"] += 0.1
    with pytest.raises(ValueError, match="sum"):
        validate_run(run)


def test_split_tokens_can_reconstruct_region_total():
    run = saved_run()
    row = run["rows"][0]
    row["tokens"] = [{"text": " r", "bits": 2, "id": 1},
                     {"text": "an", "bits": row["surprisal_bits"] - 2, "id": 2}]
    validate_run(run)


@pytest.mark.parametrize("problem", ["missing_cell", "duplicate_id", "duplicate_cell",
                                     "unknown_experiment", "unknown_factor", "unknown_level"])
def test_saved_runs_require_complete_registered_designs(problem):
    run = saved_run()
    row = run["rows"][0]
    if problem == "missing_cell":
        run["rows"].pop()
    elif problem == "duplicate_id":
        run["rows"].append(deepcopy(row))
    elif problem == "duplicate_cell":
        duplicate = deepcopy(row)
        duplicate["id"] += "-copy"
        run["rows"].append(duplicate)
    elif problem == "unknown_experiment":
        row["experiment"] = "unknown"
    elif problem == "unknown_factor":
        row["factors"]["unexpected"] = "value"
    else:
        row["factors"]["boundary"] = "unknown"
    with pytest.raises(ValueError):
        validate_run(run)


def test_cached_summary_is_not_trusted():
    run = saved_run()
    run["summary"] = {"corrupt": "ignored"}
    validate_run(run)


@pytest.mark.parametrize("field", ["id", "item", "context", "target", "spillover"])
def test_comparison_rejects_changed_materials(field):
    left = saved_run()
    right = deepcopy(left)
    if field == "item":
        for row in right["rows"]:
            row[field] += "-renamed"
    else:
        right["rows"][0][field] += " changed"
    with pytest.raises(ValueError, match="identical materials"):
        compare_runs(left, right)


def test_comparison_matches_reordered_rows_and_recomputes_summaries():
    left = saved_run()
    right = deepcopy(left)
    right["rows"].reverse()
    right["summary"] = [{"estimate": 999}]
    result = compare_runs(left, right)["summary"][0]
    assert result["estimate"] == 0
    assert result["left_estimate"] == result["right_estimate"] == 2.5
    assert all(item["delta"] == 0 for item in result["items"])


def test_comparison_rejects_incomplete_item_overlap():
    left = saved_run()
    right = deepcopy(left)
    removed = right["rows"][0]["item"]
    right["rows"] = [row for row in right["rows"] if row["item"] != removed]
    with pytest.raises(ValueError, match="identical materials"):
        compare_runs(left, right)


def shift_ambiguous_cost(run, deltas):
    for row in run["rows"]:
        if row["factors"] == {"ambiguity": "ambiguous", "boundary": "absent"}:
            delta = deltas[row["item"]]
            row["surprisal_bits"] += delta
            row["tokens"][0]["bits"] += delta


def test_constant_paired_shift_collapses_interval_despite_baseline_variation():
    left = saved_run()
    items = sorted({row["item"] for row in left["rows"]})
    shift_ambiguous_cost(left, dict(zip(items, range(len(items)), strict=True)))
    right = deepcopy(left)
    shift_ambiguous_cost(right, dict.fromkeys(items, 3))
    result = compare_runs(left, right, samples=100)["summary"][0]
    assert result["estimate"] == 3
    assert result["ci95"] == [3, 3]


def test_interval_resamples_matched_item_deltas():
    left = saved_run()
    right = deepcopy(left)
    items = sorted({row["item"] for row in left["rows"]})
    shifts = dict(zip(items, range(len(items)), strict=True))
    shift_ambiguous_cost(right, shifts)
    result = compare_runs(left, right, samples=100, seed=4)["summary"][0]
    assert result["ci95"] == bootstrap(list(shifts.values()), samples=100, seed=4)
    assert result["estimate"] == sum(shifts.values()) / len(items)
    assert [item["delta"] for item in result["items"]] == list(shifts.values())


@pytest.mark.parametrize("samples", [True, False, 0, -1, 2.5, "20", None])
def test_comparison_requires_positive_integer_samples(samples):
    with pytest.raises(ValueError, match="samples"):
        compare_runs(saved_run(), saved_run(), samples=samples)


@pytest.mark.parametrize("seed", [True, 0.5, "17", None])
def test_comparison_requires_integer_seed(seed):
    with pytest.raises(ValueError, match="seed"):
        compare_runs(saved_run(), saved_run(), seed=seed)


def test_comparison_is_repeatable_and_records_resampling_settings():
    left = saved_run()
    right = deepcopy(left)
    items = sorted({row["item"] for row in left["rows"]})
    shift_ambiguous_cost(right, dict(zip(items, range(len(items)), strict=True)))
    result = compare_runs(left, right, samples=31, seed=-5)
    assert result == compare_runs(left, right, samples=31, seed=-5)
    assert result["analysis"] == {"samples": 31, "seed": -5}


def test_comparison_preserves_each_sources_complete_metadata():
    left = saved_run()
    right = deepcopy(left)
    left["metadata"].update(revision="left-revision", notes={"environment": ["cpu"]})
    right["metadata"].update(revision="right-revision", created_utc="2026-01-01T00:00:00Z")
    result = compare_runs(left, right, samples=5)
    assert result["metadata"] == {"left": left["metadata"], "right": right["metadata"]}
    result["metadata"]["left"]["notes"]["environment"].append("changed")
    assert left["metadata"]["notes"]["environment"] == ["cpu"]


def test_materials_are_checked_directly_even_when_recorded_hashes_match():
    left = saved_run()
    right = deepcopy(left)
    left["metadata"]["stimuli_sha256"] = right["metadata"]["stimuli_sha256"] = "stale"
    right["rows"][0]["context"] += " revised"
    with pytest.raises(ValueError, match="identical materials"):
        compare_runs(left, right)


@pytest.mark.parametrize("backend,empirical", [("toy", True), ("huggingface", False)])
def test_known_backends_cannot_mislabel_empirical_status(backend, empirical):
    run = saved_run()
    run["metadata"].update(backend=backend, empirical=empirical)
    with pytest.raises(ValueError, match="contradicts empirical"):
        validate_run(run)


def test_toy_and_empirical_runs_cannot_be_silently_compared():
    left = saved_run()
    right = deepcopy(left)
    right["metadata"].update(backend="huggingface", model="test-model", empirical=True)
    with pytest.raises(ValueError, match="toy and empirical"):
        compare_runs(left, right)


def test_two_empirical_model_records_are_comparable():
    left = saved_run()
    right = deepcopy(left)
    left["metadata"].update(backend="huggingface", model="first", empirical=True)
    right["metadata"].update(backend="huggingface", model="second", empirical=True)
    assert compare_runs(left, right, samples=5)["summary"][0]["estimate"] == 0


def test_delta_direction_and_contrast_meaning_are_explicit():
    left = saved_run()
    right = deepcopy(left)
    items = {row["item"] for row in right["rows"]}
    shift_ambiguous_cost(right, dict.fromkeys(items, 2))
    forward = compare_runs(left, right, samples=5)
    reverse = compare_runs(right, left, samples=5)
    assert forward["direction"] == "right_minus_left"
    a, b = forward["summary"][0], reverse["summary"][0]
    assert a["estimate"] == 2
    assert b["estimate"] == -2
    assert b["ci95"] == [-a["ci95"][1], -a["ci95"][0]]
    assert "RIGHT" in a["interpretation"]
    assert "better model" in a["interpretation"]
    assert "missing-comma cost" in a["contrast_interpretation"]


def test_same_frame_names_in_different_experiments_remain_separate():
    left = saved_run("all")
    for row in left["rows"]:
        row["item"] = "frame-" + row["item"].rsplit("-", 1)[1]
    right = deepcopy(left)
    for row in right["rows"]:
        offset = int(row["item"].rsplit("-", 1)[1]) + 1
        row["surprisal_bits"] += offset
        row["tokens"][0]["bits"] += offset
    right["rows"].reverse()
    result = compare_runs(left, right, samples=5)
    assert len({row["key"] for row in result["summary"]}) == len(result["summary"])
    assert all(row["estimate"] == 0 and row["ci95"] == [0, 0] for row in result["summary"])


def test_comparing_different_tokenizations_preserves_input_records():
    left = saved_run()
    right = deepcopy(left)
    for row in right["rows"]:
        bits = row["surprisal_bits"] / 2
        row["tokens"] = [{"id": 1, "text": row["target"][:2], "bits": bits},
                         {"id": 2, "text": row["target"][2:], "bits": bits}]
    originals = deepcopy((left, right))
    result = compare_runs(left, right, samples=5)
    assert (left, right) == originals
    assert result["summary"][0]["estimate"] == 0


def test_relabeling_factor_cells_does_not_bypass_material_matching():
    left = saved_run()
    right = deepcopy(left)
    for row in right["rows"]:
        boundary = row["factors"]["boundary"]
        row["factors"]["boundary"] = "comma" if boundary == "absent" else "absent"
    with pytest.raises(ValueError, match="identical materials"):
        compare_runs(left, right, samples=5)
