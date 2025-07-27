from collections import Counter

import pytest

from scopeglass.stimuli import generate


def test_design_is_balanced_and_ids_unique():
    rows = generate()
    assert len(rows) == len({r.id for r in rows}) == 192
    assert set(Counter(r.item for r in rows).values()) == {8}
    for row in rows:
        assert row.target.startswith(" ")
        assert not row.context.endswith(" ")


def test_polarity_controls_are_identical_across_locations():
    rows = generate("polarity")
    for item in {r.item for r in rows}:
        controls = [r for r in rows if r.item == item and r.factors["negation"] == "absent"]
        assert len({r.context for r in controls}) == 1
        negatives = [r for r in rows if r.item == item and r.factors["negation"] == "present"]
        assert all(r.context.lower().split().count("no") == 1 for r in negatives)
        assert len({r.context for r in negatives}) == 2


def test_unknown_experiment_is_rejected():
    with pytest.raises(ValueError):
        generate("mystery")
