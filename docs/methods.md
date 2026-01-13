# Methods and interpretive limits

Scopeglass follows the logic of targeted syntactic evaluation: change a small
part of a sentence, specify a prediction at a critical region, and test that
prediction across lexical frames. The unit of analysis is the frame, not the
token or condition.

## Temporary ambiguity: NP/Z

Here NP/Z means that a verb can take a noun-phrase object or no overt object.
The ambiguity is temporary: the main verb ultimately rules out the object parse.

| Verb type | Boundary | Context | Target |
| --- | --- | --- | --- |
| optionally transitive | absent | While the hunter hunted the deer | ran |
| optionally transitive | comma | While the hunter hunted, the deer | ran |
| intransitive control | absent | While the hunter slept the deer | ran |
| intransitive control | comma | While the hunter slept, the deer | ran |

Let A denote the ambiguous verb, C the control verb, 0 no comma, and 1 a comma.
For each item:

```text
G = [S(A,0) − S(A,1)] − [S(C,0) − S(C,1)]
```

A positive G means that the comma reduces main-verb surprisal more after the
ambiguous verb. Subtracting the control estimates a punctuation effect beyond
the generic benefit of a clause-boundary cue. It does not eliminate interactions
between punctuation and individual verbs. Verb frequencies and selectional
preferences differ between A and C. Control verbs are intended to be
intransitive in these contexts, not to lack every possible transitive use.

The theoretical motivation is incremental expectation: readers maintain
expectations over upcoming material, and disambiguating input can be difficult
when it conflicts with those expectations. See [Hale (2001)](https://aclanthology.org/N01-1021/)
and [Levy (2008)](https://escholarship.org/uc/item/66v7520b).
Raw language-model surprisal is not syntax-only surprisal, a distinction studied
in [Arehalli et al. (2022)](https://aclanthology.org/2022.conll-1.20/).
Scopeglass does not fit human reading times or claim to explain their magnitude.

## Agreement attraction

Cross head number h, distractor number d, and verb number v, all singular/plural.
For example, `The key(s) to the cabinet(s)` precedes `is/are`.

```text
M(h,d) = S(verb mismatching h) − S(verb matching h)
agreement preference = mean of M over all four (h,d) contexts
attraction penalty = mean_h [M(h,h) − M(h,opposite(h))]
```

Positive preference favors the grammatical form. Positive attraction means that
a mismatching distractor reduces this preference. Averaging across head number
is a compact summary that can conceal singular/plural asymmetries; the raw
eight-cell tables should also be inspected. Both targets are full words,
scored as the sum of their subword surprisals.

## Negative polarity and scope

Compare the following, crossing `ever/often` at the marked location:

```text
The senator that the journalist interviewed has [ever/often] ...
No senator that the journalist interviewed has [ever/often] ...
The senator that no journalist interviewed has [ever/often] ...
```

On the intended reading, matrix `no` licenses matrix `ever`; the embedded `no`
does not. This probes structural licensing, which connects hierarchical syntax
to the semantic environments in which polarity items occur. It is not a general
test of negation understanding or an exhaustive account of NPI licensing.

Define an ever preference R = S(often) − S(ever). For location L:

```text
B(L) = R(negation present, L) − R(negation absent, L)
scope selectivity = B(matrix) − B(embedded)
```

Matrix benefit, embedded benefit, and selectivity are all reported. The positive
control is identical across locations; it appears twice to keep each location's
contrast explicit. These duplicate controls are neither independent observations
nor extra bootstrap units. The scorer caches identical context/target pairs.

The ever/often control mitigates lexical baseline differences but does not remove
all semantic differences. Negation location also changes its distance to the
target. A negative selectivity score is compatible with a proximity heuristic,
among other explanations; it does not prove one. Alternative parses, language
varieties, and pragmatic contexts can affect polarity judgments.

## Estimation

1. Calculate each contrast inside each lexical frame.
2. Report the arithmetic mean across frames.
3. Resample 12 frames with replacement, 2,000 times by default, using seed 17.
4. Take interpolated 2.5th and 97.5th percentiles of the bootstrap means.

These are descriptive percentile intervals, not adjusted significance tests.
They reflect item variation in this small authored set. They do not include
uncertainty from model training, participant variation, alternative templates,
or choice of scoring region. The toy oracle has identical effects across frames,
so its intervals collapse by construction.

All computations use bits. Scoring uses next-token logits shifted by one position
and sums only target-token negative log probabilities. No temperature, sampling,
chat template, added BOS/EOS token, or length normalization is applied. Models
requiring a special prompting convention need separate validation.

## Reproducibility and material revision

The checked-in run records the model's resolved Hugging Face commit and loads
the tokenizer from that same revision. A SHA-256 hash covers every generated
stimulus including its factors and displayed spillover. Float32 CPU results may
differ slightly across numerical libraries or devices. The package list from the
measured environment is saved beside the results; it is an environment record,
not a portable lockfile for every platform.

During material review, the sailor frame's control verb was changed from
`rested` to `shivered`: `rested the boat` admits a transitive reading, undermining
its role as the intransitive control. The checked-in run uses the revised frame.
No frames were excluded because of the sign of their measured effect.
