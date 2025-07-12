from scopeglass.analysis import analyze
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate_np_s


def test_np_s_crosses_verb_selection_with_explicit_complementizer():
    rows = generate_np_s()
    assert len(rows) == len({row.id for row in rows}) == 48
    for item in {row.item for row in rows}:
        cells = [row for row in rows if row.item == item]
        assert len(cells) == 4
        assert len({row.target for row in cells}) == 1
        assert sum(" that " in row.context for row in cells) == 2
        assert sum(" insisted" in row.context for row in cells) == 2


def test_np_s_interaction_removes_the_generic_boundary_benefit():
    scorer = ToyScorer()
    rows = [{**row.to_dict(), **scorer.score(row)} for row in generate_np_s()]
    result = analyze(rows, samples=20)
    assert len(result) == 1
    assert result[0]["key"] == "np_s"
    assert result[0]["estimate"] == 2.5
    assert result[0]["n_items"] == 12
