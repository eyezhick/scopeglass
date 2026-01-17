# Working with a report

Open `report.html` in a browser. The page includes its run data, JavaScript, and
styles; it needs neither a server nor an internet connection. JavaScript must be
enabled. To rebuild the page after updating Scopeglass:

```sh
scopeglass report runs/latest/results.json --out runs/latest/report.html
```

Start with the provenance strip. A **measured run** contains model scores;
a **toy oracle** contains stipulated values used to check the experiment and
analysis plumbing. Toy intervals can collapse to a point because every frame
was assigned the same effect. That is not evidence of unusual model precision.
The recorded timestamp is run metadata, not the time you opened the page.

## Read an effect, then inspect its sentences

The large numbers are paired contrasts in bits, not average sentence scores.
Their signs are explained beside each estimate and in the methods disclosure.
Green dots are lexical-frame effects. The orange point is the mean, and the
orange line is the 95% bootstrap interval. Every chart has its own labeled,
symmetric scale: two dots equally far from zero in different charts need not
represent the same effect size.

The interval describes variation among the authored frames. It does not measure
uncertainty across model training runs or human readers. An interval crossing
zero and an interval excluding zero are both worth inspecting at the item level.
See [the methods](methods.md) for the contrast definitions and confounds.

The evidence table supports a few useful paths through that inspection:

- Select an experiment, then a lexical frame, to compare its conditions.
- Search the displayed sentence text. Search ignores case and surrounding spaces.
- Order by high surprisal to find difficult targets, or by low surprisal to find
  expected ones. Material order restores the run's original order.
- Open a target's token disclosure to see each decoded piece, its surprisal, and
  its tokenizer ID when available. Quoted token text makes spaces and newlines
  visible. The target score sums its token scores; it is not length-normalized.

Filters affect the sentence table, not the effect cards. The overview and cards
continue to describe the complete run. Experiment choices and frame counts come
from the loaded data, so an older three-experiment run remains understandable.
An NP/S run adds notes about the temporary object/clause ambiguity and the
explicit complementizer *that*.

The default page holds 24 conditions. Choose 48, 96, or All for a wider view.
Changing a filter returns to the first page. Reset filters restores all
experiments and frames, clears search, restores material order, and focuses the
search box. It keeps the page-size preference.

## Take the evidence elsewhere

**Export filtered CSV** saves every matching condition in the selected order,
including conditions on other pages. It includes the factors, all sentence
regions, full-precision target score, and token records. Factors and tokens are
JSON inside CSV fields. Commas, quotation marks, and newlines are quoted correctly.
Text beginning with a spreadsheet formula operator, optionally after whitespace,
is prefixed with an apostrophe. This prevents a sentence from executing as a
formula when opened in a spreadsheet; use JSON when exact original strings matter.

**Download complete run JSON**, inside the provenance disclosure, preserves the
whole run regardless of the current filters. It includes rows, summary estimates,
analysis settings, and metadata, and can be passed back to `scopeglass report`.

A filtered report still embeds the whole run. To share only the selected rows,
use CSV. Sharing the HTML shares its complete underlying dataset.

Printing includes all conditions matching the current filters, with token
details expanded and a written record of those filters. Pagination controls and
buttons are hidden. Closing print preview restores the current page. For a
shorter printout, narrow the experiment or lexical frame first.

Keyboard users can skip directly to the evidence section, move through the
controls with Tab, expand token details with Enter or Space, and scroll the
focused table region horizontally on narrow displays. No external scripts,
fonts, or stylesheets are loaded by the report.
