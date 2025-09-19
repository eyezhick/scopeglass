import copy

import pytest

from scopeglass.analysis import analyze, bootstrap
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate


def toy_rows():
    scorer = ToyScorer()
    return [{**row.to_dict(), **scorer.score(row)} for row in generate()]


def test_known_contrast_signs_and_values():
    results = {r["key"]: r for r in analyze(toy_rows(), samples=30)}
    expected = {"garden_path": 2.5, "agreement_margin": 2.5, "attraction": 1.0,
                "matrix_licensing": 4.0, "embedded_licensing": 0.0, "scope_selectivity": 4.0}
    assert {k: r["estimate"] for k, r in results.items()} == expected
    assert all(r["n_items"] == 12 for r in results.values())


def test_item_specific_offsets_cancel():
    rows = toy_rows()
    shifted = copy.deepcopy(rows)
    for row in shifted:
        row["surprisal_bits"] += int(row["item"].split("-")[1]) * 17
    assert analyze(rows, samples=10) == analyze(shifted, samples=10)


@pytest.mark.parametrize("problem", ["missing", "duplicate", "nan", "factor", "negative"])
def test_broken_designs_fail_loudly(problem):
    rows = toy_rows()
    if problem == "missing":
        rows.pop()
    elif problem == "duplicate":
        rows.append(rows[0])
    elif problem == "nan":
        rows[0]["surprisal_bits"] = float("nan")
    elif problem == "negative":
        rows[0]["surprisal_bits"] = -1
    else:
        rows[0]["factors"]["boundary"] = "invented"
    with pytest.raises(ValueError):
        analyze(rows)


def test_bootstrap_is_seeded_and_resamples_items():
    assert bootstrap([1, 2, 9], seed=7) == bootstrap([1, 2, 9], seed=7)
    assert bootstrap([3] * 12) == [3, 3]
    low, high = bootstrap([1, 2, 9])
    assert low < 4 < high
