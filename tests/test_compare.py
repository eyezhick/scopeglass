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
