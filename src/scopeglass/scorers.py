"""Critical-region surprisal, in bits. No generation or grammaticality prompting."""

import math
from functools import lru_cache

from .stimuli import Stimulus


class ToyScorer:
    """A stipulated oracle for checking contrast signs; not empirical evidence."""

    metadata = {"backend": "toy", "model": "illustrative-oracle", "empirical": False}

    def score(self, row: Stimulus) -> dict:
        f = row.factors
        if row.experiment == "garden_path":
            bits = 4.0 + (f["boundary"] == "absent") * (
                3.0 if f["ambiguity"] == "ambiguous" else 0.5
            )
        elif row.experiment == "agreement":
            bits = 3.0 if f["head"] == f["verb"] else 6.0
            if f["head"] != f["distractor"]:
                bits += 0.5 if f["head"] == f["verb"] else -0.5
        else:
            licensed = f["location"] == "matrix" and f["negation"] == "present"
            bits = (3.0 if licensed else 7.0) if f["target"] == "npi" else 4.0
        return {"surprisal_bits": bits, "tokens": [{"text": row.target, "bits": bits}]}


def continuation_start(prefix_ids: list[int], full_ids: list[int]) -> int:
    """Reject tokenizers that merge across the experimental region boundary."""
    if not prefix_ids:
        raise ValueError("Scoring requires a nonempty tokenized left context")
    n = len(prefix_ids)
    if full_ids[:n] != prefix_ids:
        raise ValueError("Tokenizer merged across context/target boundary; revise the boundary")
    if len(full_ids) <= n:
        raise ValueError("Target must contain at least one token")
    return n


class HuggingFaceScorer:
    def __init__(self, model: str, revision: str | None = None, device: str = "cpu"):
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.model = AutoModelForCausalLM.from_pretrained(
            model, revision=revision, trust_remote_code=False, use_safetensors=True,
        ).to(device).eval()
        resolved = getattr(self.model.config, "_commit_hash", None) or revision
        self.tokenizer = AutoTokenizer.from_pretrained(
            model, revision=resolved, trust_remote_code=False,
        )
        self.metadata = {
            "backend": "huggingface", "model": model, "revision": resolved,
            "device": device, "empirical": True, "torch": torch.__version__,
            "transformers": transformers.__version__, "dtype": str(self.model.dtype),
        }

    def score(self, row: Stimulus) -> dict:
        return self.score_text(row.context, row.target)

    @lru_cache(maxsize=2048)
    def score_text(self, context: str, target: str) -> dict:
        torch = self.torch
        prefix = self.tokenizer.encode(context, add_special_tokens=False)
        ids = self.tokenizer.encode(context + target, add_special_tokens=False)
        start = continuation_start(prefix, ids)
        limit = getattr(self.model.config, "max_position_embeddings", None)
        if limit is not None and len(ids) > limit:
            raise ValueError(f"Input has {len(ids)} tokens, exceeding model limit {limit}")
        inputs = torch.tensor([ids], device=self.model.device)
        with torch.inference_mode():
            logits = self.model(input_ids=inputs, use_cache=False).logits[0]
            # Position t-1 predicts token t. Score only the continuation, never the context.
            log_probs = logits[start - 1:-1].float().log_softmax(-1)
            labels = inputs[0, start:]
            bits = (-log_probs.gather(1, labels[:, None]).squeeze(1) / math.log(2)).tolist()
        tokens = [
            {"id": token_id, "text": self.tokenizer.decode([token_id]), "bits": value}
            for token_id, value in zip(ids[start:], bits, strict=True)
        ]
        return {"surprisal_bits": sum(bits), "tokens": tokens}
