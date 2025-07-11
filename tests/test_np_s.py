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
