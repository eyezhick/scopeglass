# The ambiguity lab

The interactive demo lets you change experimental conditions and inspect their
measured surprisal. It serves two saved model runs, their paired comparison, and
two standalone reports. It does not send text to a model or require an API key.

[Open the live demo](https://eyezhick.github.io/scopeglass/).
The demo is public on GitHub Pages and requires no sign-in.

## Run it locally

From the repository root, with Scopeglass installed:

```sh
python scripts/build_demo.py
python -m http.server 8000 --directory demo
```

Visit `http://localhost:8000`. Use a local HTTP server because the page loads JSON
with `fetch`; opening `demo/index.html` directly as a `file:` URL may be blocked
by the browser. The individual report HTML files can be opened directly offline.

## What to try

1. In Garden paths, switch between a comma and no comma. Then change the verb.
   Watch all four condition bars rather than only the selected score.
2. Choose Objects or clauses? and add *that*. Change models while retaining the
   same frame and condition. Some frames do not follow the aggregate direction.
3. In The nearest noun, keep the subject singular and pluralize the distractor.
   Compare *is* with *are*, then repeat with a plural subject.
4. In Where “no” reaches, move negation into the relative clause. Compare *ever*
   against *often* and check the conditions without negation.
5. Scroll to the effect plots. Dots show frame effects; intervals summarize the
   bootstrap over frames. Each plot has its own labeled scale around zero.

The probability slider is a separate explanation of the surprisal formula; it
does not alter measured scores. Model and condition changes announce the selected
score to assistive technology. Controls use ordinary buttons and selects, so
they also work from the keyboard.

## Build a static copy

```sh
python scripts/build_demo.py --out runs/demo-site
```

The output directory contains everything the demo needs. The builder validates
both source runs, rejects toy scores, recomputes summaries and paired comparisons,
and regenerates the reports. It preserves measurement metadata and never runs
inference. No remote fonts, chart libraries, or analytics are loaded.

Source assets are `demo/index.html`, `demo/style.css`, and `demo/app.js`.
Measurements live under `examples/distilgpt2-v2/` and `examples/gpt2-v2/`.
`tests/test_demo.py` checks that the built bundle preserves those measurements,
resolves its local links, and pairs the models in the documented direction.
The hosted copy is built by `.github/workflows/pages.yml` and published to GitHub
Pages on pushes to `main`. The workflow checks the demo bundle before publishing;
all assets use relative paths so they work under the `/scopeglass/` project path.
