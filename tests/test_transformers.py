"""Check against Transformers' own masked-label loss without downloading weights."""

import math

import pytest

from scopeglass.scorers import HuggingFaceScorer


def test_surprisal_matches_transformers_reference_loss():
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    torch.manual_seed(7)
    config = transformers.GPT2Config(vocab_size=8, n_positions=16, n_embd=16, n_layer=1,
                                    n_head=2, bos_token_id=0, eos_token_id=0)
    model = transformers.GPT2LMHeadModel(config).eval()

    class Tokenizer:
        def encode(self, text, **kwargs):
            return [1, 2] if text == "prefix" else [1, 2, 3, 4, 5]

        def decode(self, ids):
            return str(ids[0])

    scorer = HuggingFaceScorer.__new__(HuggingFaceScorer)
    scorer.torch, scorer.model, scorer.tokenizer = torch, model, Tokenizer()
    actual = scorer.score_text("prefix", " target")
    inputs = torch.tensor([[1, 2, 3, 4, 5]])
    labels = torch.tensor([[-100, -100, 3, 4, 5]])
    with torch.inference_mode():
        reference = model(input_ids=inputs, labels=labels).loss.item() * 3 / math.log(2)
    assert actual["surprisal_bits"] == pytest.approx(reference, rel=1e-6)
