import math
from types import SimpleNamespace

import pytest

from scopeglass.scorers import HuggingFaceScorer, continuation_start


@pytest.mark.parametrize("prefix,full", [([], [1]), ([1], [2, 3]), ([1], [1])])
def test_invalid_boundaries_fail(prefix, full):
    with pytest.raises(ValueError):
        continuation_start(prefix, full)


def test_boundary_accepts_multiple_target_tokens():
    assert continuation_start([1, 2], [1, 2, 3, 4]) == 2


def test_causal_shift_multitoken_sum_and_context_exclusion():
    torch = pytest.importorskip("torch")

    class Tokenizer:
        def encode(self, text, **kwargs):
            return {"context": [0, 1], "context target": [0, 1, 2, 3]}[text]

        def decode(self, ids):
            return str(ids[0])

    class Model:
        device = "cpu"
        config = SimpleNamespace(max_position_embeddings=8)

        def __call__(self, **kwargs):
            # Unequal rows catch scoring the wrong position or including the context.
            probs = torch.tensor([[
                [.7, .1, .1, .1], [.1, .1, .5, .3],
                [.1, .1, .55, .25], [.25, .25, .25, .25],
            ]])
            return SimpleNamespace(logits=probs.log())

    scorer = HuggingFaceScorer.__new__(HuggingFaceScorer)
    scorer.torch, scorer.model, scorer.tokenizer = torch, Model(), Tokenizer()
    result = scorer.score_text("context", " target")
    assert result["surprisal_bits"] == pytest.approx(-math.log2(.5 * .25))
    assert [t["id"] for t in result["tokens"]] == [2, 3]
    scorer.model.config.max_position_embeddings = 3
    scorer.score_text.cache_clear()
    with pytest.raises(ValueError, match="exceeding"):
        scorer.score_text("context", " target")
