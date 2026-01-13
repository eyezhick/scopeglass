# Scopeglass

**A sentence can lead you down the wrong path. Does a language model feel the turn?**

> While the hunter hunted the deer **ran** into the woods.

Until *ran*, the deer could be what the hunter hunted. Then the sentence asks you
to take it apart and put it back together. Scopeglass measures what happens at
that turn: how a model's expectations change when syntax, punctuation, and scope
pull in different directions.

This is a small experimental instrument, built around three questions:

| Experiment | Manipulation | Question |
| --- | --- | --- |
| Garden paths · NP/Z | Ambiguous/intransitive verb × comma/no comma | Does a boundary cue prevent a reanalysis cost? |
| Agreement attraction | Subject number × distractor number × verb number | Does a nearby noun pull agreement away from the subject? |
| Polarity & scope | Matrix/embedded negation × presence × ever/often | Is a negation useful because of its structural position, or just its presence? |

There are 12 original lexical frames per experiment, 240 conditions, and six
explicit contrasts. Every aggregate can be traced back to its sentences and
token scores. The report is one self-contained HTML file; it works offline.

## Try it

Python 3.11 or newer. No API key, server, or model download is needed for the toy run.

```sh
git clone https://github.com/eyezhick/scopeglass.git
cd scopeglass
python -m venv .venv
source .venv/bin/activate
pip install -e .
scopeglass run --out runs/toy
```

Open `runs/toy/report.html` in a browser. The toy scorer supplies stipulated
values to exercise the analysis; its reports are labeled accordingly.

For a real model:

```sh
pip install -e '.[models]'
scopeglass run --backend hf --model distilbert/distilgpt2 \
  --revision 2290a62682d06624634c1f46a6ad5be0f47f38aa \
  --out runs/distilgpt2
```

The first run downloads model weights from Hugging Face. CPU is the default;
`--device mps` or `--device cuda` selects an available accelerator. DistilGPT-2
has been run end to end; other causal models use the same adapter but have not
been individually validated. Remote model code is disabled, and weights must
be available as safetensors.

A [measured DistilGPT-2 run](examples/distilgpt2/results.json) and its
[offline report](examples/distilgpt2/report.html) are checked in. Download the
HTML file and open it locally; GitHub's source viewer does not execute it.
Read the [first-run notes](docs/first-run.md) for what the effects do and don't say.

## What is being measured?

For a target made of tokens t₁…tₙ after context c:

```text
S(target | c) = −Σ log₂ P(tᵢ | c, t₁…tᵢ₋₁)
```

The target is scored with its leading space. Context tokens and the displayed
spillover are excluded. Multi-token words are summed, never averaged. The
tokenizer must preserve the context as a prefix of the complete token sequence;
if it merges across the region boundary, the scorer refuses the example.

This is **lexical token surprisal**, not a direct estimate of uncertainty over
parse trees. The design makes structural predictions testable through contrasts.
It does not identify the model's internal parsing algorithm.

Uncertainty comes from a seeded, paired bootstrap over lexical frames. Four or
eight conditions from the same frame stay together. Duplicate cells, missing
conditions, and non-finite scores are rejected. The [methods](docs/methods.md)
give the equations, predicted signs, and confounds.

## Working with the materials

```sh
scopeglass stimuli --experiment garden_path > garden-paths.jsonl
scopeglass run --backend hf --experiment garden_path --out runs/npz
scopeglass report examples/distilgpt2/results.json --out runs/rebuilt.html
```

Add lexical frames in `src/scopeglass/stimuli.py`. A new experiment also needs
its factorial design and contrast in `analysis.py`, and a test with a known
answer. Runs save the full materials, their SHA-256 hash, token IDs, resolved
model revision, package versions, device, and bootstrap seed.

## Development

```sh
pip install -e '.[dev]'
ruff check src tests
pytest -q
python -m build
```

With the `models` extra installed, tests also compare the scorer against a tiny
random GPT-2 model's own masked-label loss. That test needs no network or weights.

The package deliberately has no runtime dependencies until a model is requested.
No telemetry, paid inference, or hidden judging model.

## Where this could go

The next useful step is to distinguish **structural uncertainty** from **semantic
plausibility**: hold the syntax fixed while changing whether the ambiguous noun
is a plausible object. A stronger garden-path effect for plausible objects would
connect incremental parsing to event knowledge. NP/S ambiguities, PP attachment,
and matched comparisons across model sizes are also natural extensions.

Those are research directions, not implemented features. Before making stronger
claims, these authored English materials need independent acceptability review,
more lexical coverage, and human reading-time comparisons.

## Reading behind the experiments

- [Hale (2001): A Probabilistic Earley Parser as a Psycholinguistic Model](https://aclanthology.org/N01-1021/).
- [Levy (2008): Expectation-based syntactic comprehension](https://escholarship.org/uc/item/66v7520b).
- [Marvin & Linzen (2018): Targeted Syntactic Evaluation of Language Models](https://arxiv.org/abs/1808.09031).
- [A Systematic Assessment of Syntactic Generalization in Neural Language Models (2020)](https://aclanthology.org/2020.acl-main.158/).
- [Syntactic Surprisal From Neural Models Predicts, But Underestimates, Human Processing Difficulty From Syntactic Ambiguities (2022)](https://aclanthology.org/2022.conll-1.20/).
- [Bylinina & Tikhonov (2022): Transformers in the loop: Polarity in neural models of language](https://aclanthology.org/2022.acl-long.455/).

Scopeglass is an independent implementation with newly authored materials. It
does not reproduce any of these papers' datasets or experiments exactly.

MIT licensed, including the original sentence materials. Model weights retain
their own licenses and are not distributed here.
