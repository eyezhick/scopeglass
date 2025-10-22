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
