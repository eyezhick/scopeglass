from copy import deepcopy
from statistics import mean

from scopeglass.diagnostics import item_diagnostics
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate


def run_with_effects(effects):
    scorer = ToyScorer()
    rows = []
    items = {}
    for stimulus in generate("garden_path"):
        if stimulus.item not in items:
            items[stimulus.item] = len(items)
        index = items[stimulus.item]
        if index >= len(effects):
            continue
        row = {**stimulus.to_dict(), **scorer.score(stimulus)}
        if stimulus.factors == {"ambiguity": "ambiguous", "boundary": "absent"}:
            row["surprisal_bits"] += effects[index] - 2.5
            row["tokens"][0]["bits"] = row["surprisal_bits"]
        rows.append(row)
    return {"schema_version": 1, "metadata": dict(scorer.metadata), "rows": rows}


def test_ranks_absolute_effects_and_retains_signed_values():
    result = item_diagnostics(run_with_effects([1, -4, 2]))
    assert [row["value"] for row in result] == [-4, 2, 1]
    assert [row["absolute_rank"] for row in result] == [1, 2, 3]
    assert all(row["mean"] == mean([1, -4, 2]) for row in result)
    assert result[0]["deviation"] == -4 - mean([1, -4, 2])


def test_equal_magnitude_frames_have_stable_item_tiebreak():
    run = run_with_effects([2, -2, 2])
    baseline = item_diagnostics(run)
    run["rows"].reverse()
    assert item_diagnostics(run) == baseline
    assert [row["item"] for row in baseline] == sorted(row["item"] for row in baseline)


def test_diagnostics_recompute_without_modifying_saved_run():
    run = run_with_effects([1, 3])
    run["summary"] = "stale"
    original = deepcopy(run)
    assert [row["value"] for row in item_diagnostics(run)] == [3, 1]
    assert run == original
