# A first look through Scopeglass

The measured run uses `distilbert/distilgpt2`, revision
`2290a62682d06624634c1f46a6ad5be0f47f38aa`, on CPU in float32. The 240 conditions
come from 36 lexical frames. Each experiment has 12 frames; the same frames
contribute to multiple contrasts within that experiment.

| Contrast | Mean, bits | 95% item-bootstrap interval |
| --- | ---: | ---: |
| Garden-path interaction | +1.029 | [−0.739, +2.810] |
| Agreement preference | +5.378 | [+5.113, +5.647] |
| Attraction penalty | +1.284 | [+1.037, +1.565] |
| Matrix licensing benefit | +1.296 | [+0.997, +1.619] |
| Embedded negation benefit | +10.971 | [+9.575, +12.184] |
| Scope selectivity | −9.675 | [−10.841, −8.468] |

The model prefers the grammatical agreement form, and the mismatching distractor
weakens that preference. This is the cleanest pattern in this set.

Garden paths are less tidy. The mean interaction is positive, but the interval
crosses zero. Some lexical frames show substantial effects in the predicted
direction; others reverse. It would be premature to call this a reliable general
garden-path effect. The positive example on the report's cover is an illustration,
not a substitute for the whole set.

Polarity gives the most useful surprise. Embedded negation has a much larger
effect on the ever/often preference than matrix negation. For the senator frame,
`ever` is about 11.20 bits after matrix negation and 2.04 bits after embedded
negation. These values go against the intended structural-licensing prediction.
Proximity to `no` is one possible explanation; this design does not isolate it
from alternative parses or lexical and discourse effects.

The next experiment should separate position from distance, and the next model
comparison should retain these materials unchanged. Changing the items until a
model gives the desired result would answer a different question.

## Inspect or reproduce

The [raw results](../examples/distilgpt2/results.json) contain every sentence,
token ID, score, item contrast, and run setting. Download the
[HTML report](../examples/distilgpt2/report.html) to browse them offline.

```sh
scopeglass run --backend hf --model distilbert/distilgpt2 \
  --revision 2290a62682d06624634c1f46a6ad5be0f47f38aa \
  --bootstrap 2000 --seed 17 --threads 4 --out runs/reproduction
```

These observations describe one small model on one authored set. The
[methods](methods.md) explain why the intervals should not be interpreted as a
population-level grammar score or a claim about human comprehension.
