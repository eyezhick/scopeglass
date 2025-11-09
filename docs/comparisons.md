# Comparing two saved runs

A model change can move every score without changing its response to syntax.
Scopeglass compares the *within-frame contrasts*, then pairs those contrasts
across runs. It does not subtract raw perplexities or count token observations
as independent evidence.

```python
import json
from pathlib import Path
from scopeglass.compare import compare_runs

left = json.loads(Path("runs/baseline/results.json").read_text())
right = json.loads(Path("runs/candidate/results.json").read_text())
comparison = compare_runs(left, right, samples=2000, seed=17)
Path("comparison.json").write_text(json.dumps(comparison, indent=2, allow_nan=False))
```

For frame `i`, let `L_i` and `R_i` be the same factorial contrast from the left
and right run. The reported delta is:

```text
d_i = R_i - L_i
estimate = mean_i(d_i)
```

The interval resamples the **paired deltas** with replacement, keeping the
number of frames fixed. It reports the interpolated 2.5th and 97.5th percentiles
of the resampled means. Subtracting endpoints of two separate intervals would
lose the pairing. For example, large variation in `L_i` is irrelevant if every
`R_i` equals `L_i + 1`: all paired deltas, and both interval endpoints, are one.

Positive always means a larger contrast on the right. It does not mean a better
language model. A larger agreement preference and a larger attraction penalty
have different interpretations. Each output contrast includes both the delta
direction and the original contrast's sign interpretation. Units are bits.

## What is allowed to differ?

Model names, revisions, environments, tokenization, and scores can differ.
Each source's full metadata is copied into the comparison for inspection.
Different tokenizations are legitimate because the target is the same text and
its score is a sum over the model's own tokens. Compare these sums, not averages
per subword. Metadata is provenance supplied by the source run; validation
cannot authenticate a claimed model revision or establish that a score was
actually measured.

The following must agree for every stimulus ID: experiment, lexical frame,
context, target, spillover, and factors. Both runs must contain exactly the same
complete factorial frames. Row order does not matter. A subset of frames is
acceptable only if both runs contain that same subset. To compare revised
materials, score a shared material set first. A matching recorded hash does not
bypass the direct material check.

`validate_run(run)` checks schema version 1, required field types, nonempty target
tokens, finite nonnegative surprisal, token-sum consistency, and complete
registered factorial designs. Token IDs are optional for the toy oracle. Cached
summaries are ignored and recomputed from raw scores. Toy and empirical runs
cannot be compared with each other; known backends must also have consistent
empirical flags. Validation raises `ValueError` with the relevant field or design.

## Finding influential frames

```python
from scopeglass.diagnostics import item_diagnostics

for frame in item_diagnostics(right):
    print(frame["key"], frame["item"], frame["value"], frame["mean_shift"])
```

Frames are sorted within each contrast by descending absolute effect, with
lexical-frame ID breaking ties. `value` retains the signed contrast;
`deviation = value - mean`. The sequential `absolute_rank` therefore has a
stable order even when magnitudes tie; it is not a statistical rank test.

For `n > 1`, `leave_one_out` is the arithmetic mean of the other `n - 1` frame
effects, and `mean_shift = leave_one_out - mean`. Both fields are `null` for a
single-frame run. These diagnostics identify sentences worth inspecting, not
frames to delete after looking at the outcome. They do not rerun the model or
change the saved experiment.

Intervals reflect variation in the authored lexical frames. They do not account
for model-training variation, the selection of templates or contrast, human
participant variation, or repeated comparisons. A collapsed interval can result
from identical toy effects or a single frame; it does not establish certainty.

## A small example you can calculate by hand

This example uses stipulated toy scores, not a measured language-model result.
Keep two NP/Z frames and increase only the ambiguous, comma-absent cell of the
second frame by four bits. The baseline effects are `[2.5, 2.5]`; the right-hand
effects become `[2.5, 6.5]`. Their paired deltas are `[0, 4]`.

```python
from copy import deepcopy
from scopeglass.compare import compare_runs
from scopeglass.diagnostics import item_diagnostics
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate

scorer = ToyScorer()
stimuli = generate("garden_path")
frames = sorted({row.item for row in stimuli})[:2]
left = {
    "schema_version": 1,
    "metadata": dict(scorer.metadata),
    "rows": [{**row.to_dict(), **scorer.score(row)}
             for row in stimuli if row.item in frames],
}
right = deepcopy(left)
for row in right["rows"]:
    if (row["item"] == frames[1]
            and row["factors"] == {"ambiguity": "ambiguous", "boundary": "absent"}):
        row["surprisal_bits"] += 4
        row["tokens"][0]["bits"] += 4

contrast = compare_runs(left, right)["summary"][0]
assert contrast["left_estimate"] == 2.5
assert contrast["right_estimate"] == 4.5
assert contrast["estimate"] == 2
assert contrast["ci95"] == [0, 4]
assert [row["mean_shift"] for row in item_diagnostics(right)] == [-2, 2]
```

The larger frame comes first in the diagnostics. Removing it lowers the right
mean from 4.5 to 2.5; removing the other frame raises the mean to 6.5. The
comparison asks how much the contrast changed; the diagnostic asks how sensitive
one run's mean is to each frame. Neither operation supports deleting the larger
frame simply because it changes the answer.
