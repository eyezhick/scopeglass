from copy import deepcopy

import pytest

from scopeglass.compare import validate_run
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
