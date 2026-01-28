# Two models, the same questions

The expanded suite contains 288 conditions in 48 lexical frames: twelve each for
NP/Z ambiguity, NP/S ambiguity, agreement, and polarity. Each model scored every
condition on CPU in float32, using the same materials. These are measured model
outputs, not toy values.

| Model | Resolved Hugging Face revision |
| --- | --- |
| `distilbert/distilgpt2` | `2290a62682d06624634c1f46a6ad5be0f47f38aa` |
| `openai-community/gpt2` | `607a30d783dfa663caf39e06633721c8d4cfcd7e` |

The recorded environment is Python 3.14.6, PyTorch 2.14.1, Transformers 4.57.6,
and Scopeglass 0.1.0. The saved run metadata retains the actual measurement time
and software versions. Later report generation does not change that provenance.
The materials fingerprint for both runs is
`b08482960b79dac5eff99c0246055b3172cebf8b9737fdea3dedd5414592395e`.

## What changed between models?

Differences below are **GPT-2 minus DistilGPT-2**. Intervals come from 2,000 paired
bootstrap samples with seed 17. Each resample keeps the two models' measurements
for a lexical frame together.

| Contrast | Difference, bits | 95% bootstrap interval |
| --- | ---: | ---: |
| NP/Z garden path | 3.386 | [2.041, 4.762] |
| NP/S ambiguity | 0.352 | [0.075, 0.662] |
| Scope selectivity | 14.006 | [12.468, 15.357] |

These are differences in experimental contrasts, not differences in overall
model quality. Greater agreement attraction, for instance, means more
susceptibility to the distractor under this contrast. A larger number is not
uniformly desirable. The complete seven-contrast result, including per-frame
left, right, and difference values, is in
[`model-comparison.json`](../examples/model-comparison.json).

## Don't stop at the mean

The NP/S average is positive for both models. But on *The editor knew the author
was exhausted*, the four-condition interaction is approximately −0.09 bits for
DistilGPT-2 and +0.59 bits for GPT-2. The figures include this frame precisely
because a smooth aggregate can hide an uncooperative example.

Scope selectivity changes sign between models: −9.68 bits for DistilGPT-2 and
+4.33 bits for GPT-2. Yet GPT-2's senator frame has a negative scope contrast
(about −2.55 bits). A positive aggregate doesn't guarantee the intended structural
pattern on every item. Inspect the raw *ever/often* baselines as well as the two
negation locations before drawing a grammatical conclusion.

The control verb *insisted* repeats across the twelve NP/S frames. The bootstrap
therefore cannot measure generalization across independent control verbs. The
polarity materials can also admit alternative readings or continuation
expectations. Neither uncertainty interval corrects these design limitations.

## Recompute without downloading a model

```sh
scopeglass compare examples/distilgpt2-v2/results.json \
  examples/gpt2-v2/results.json --out runs/comparison.json
scopeglass diagnose examples/gpt2-v2/results.json --out runs/items.json
python scripts/build_demo.py
```

For model reruns, use the revisions above with `scopeglass run --backend hf`.
The [methods](methods.md) define every contrast; the [comparison guide](comparisons.md)
explains strict matching and diagnostics. The original 240-condition DistilGPT-2
run remains under `examples/distilgpt2/` and is described in [first-run.md](first-run.md).
