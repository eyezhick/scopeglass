# Working with custom materials

Scopeglass treats a lexical frame as the unit of comparison. Keep all of its
factorial cells together when editing, selecting, or exporting materials. A
garden-path frame has four cells; an agreement frame has eight. Cutting the first
ten rows out of a file can leave the final frame unusable.

The dependency-free `scopeglass.materials` module handles those checks before a
model needs to be loaded:

```python
from pathlib import Path

from scopeglass.materials import (
    describe_materials,
    load_csv,
    load_jsonl,
    select_items,
    write_csv,
    write_jsonl,
)
from scopeglass.stimuli import generate

rows = select_items(generate("garden_path"), limit=3)
write_jsonl(rows, Path("my-materials.jsonl"))
write_csv(rows, Path("my-materials.csv"))

assert load_jsonl(Path("my-materials.jsonl")) == rows
assert load_csv(Path("my-materials.csv")) == rows
description = describe_materials(rows)
assert description["n_stimuli"] == 12
assert description["n_items"] == 3
```

## File formats

JSONL contains one full stimulus object per nonblank line. These are the seven
required fields, shown for one cell of a frame:

```json
{"id":"npz-00-ambiguous-absent","item":"npz-00","experiment":"garden_path","context":"While the hunter hunted the deer","target":" ran","spillover":" into the woods.","factors":{"ambiguity":"ambiguous","boundary":"absent"}}
```

All fields except `factors` are strings. `spillover` may be empty. Other strings
must contain at least one non-whitespace character. Spaces in `target` and
`spillover` are preserved because they affect tokenization; no loader trims or
inserts spaces. The sentence is `context + target + spillover`.

CSV uses the same seven columns. The `factors` cell holds a JSON object, such as
`{"ambiguity": "ambiguous", "boundary": "absent"}`. Use `write_csv` to handle
quoting around JSON, commas, quotation marks, and line breaks. Both exports use
UTF-8 and stable factor-key ordering. Imports accept UTF-8 with or without a BOM.
CSV columns may appear in any order, but each must occur exactly once.

Loaders reject extra fields, including scores from a results file. An exported
materials file describes inputs, so edits cannot accidentally reuse old scores.
Malformed JSON and CSV errors include the filename and physical line number;
errors involving a complete design identify the filename and offending item.

## What validation checks

`validate_materials(rows)` raises `ValueError` for an empty dataset, malformed
record types, duplicate stimulus ids, unregistered experiments, wrong factor
names or levels, duplicate cells, and incomplete frames. It returns `None` on
success. Loaders, exporters, selection, hashing, and descriptions all validate
their input.

A frame is an `(experiment, item)` pair. Its cells must be the full Cartesian
product of the levels in `scopeglass.analysis.DESIGNS`. Validation consults that
registry at call time. Adding an experiment also requires the corresponding
analysis implementation; a factor declaration alone does not define a contrast.

Identical sentence text is allowed. In the polarity experiment, positive controls
are intentionally repeated across the matrix and embedded location conditions.
They are distinct design cells despite having the same surface form.

These checks establish design completeness, not linguistic validity. Review
edited sentences for plausible continuations and unwanted differences between
conditions. Hold the disambiguating target constant when the intended contrast
depends on comparing that same word across contexts.

## Selecting and inspecting frames

| Function | Behavior |
| --- | --- |
| `select_items(rows, items=None, limit=None)` | Return a new list containing whole frames in source order. |
| `material_hash(rows)` | Return the SHA-256 fingerprint used for run reproducibility. |
| `describe_materials(rows)` | Return row counts, frame counts, factor levels, and the fingerprint. |

An explicit `items` list selects item ids, not stimulus ids. Unknown ids fail
instead of disappearing silently. An empty list is invalid; `None` selects all
items. Repeating an item id does not duplicate its rows. If two experiments use
the same item id, that id selects both frames.

`limit` must be a positive integer; booleans are rejected. It applies after the
explicit item selection and counts `(experiment, item)` frames in order of first
appearance. Even interleaved rows remain complete. A limit larger than the
available number of frames returns all selected frames. The order of ids in the
request does not change source order.

The description contains `n_stimuli`, `n_items`, `experiments`, and `material_hash`.
`experiments` maps each experiment name to its own `n_stimuli`, `n_items`, and
`factors` mapping. Factor values are lists of registered levels. The result is
JSON-serializable and counts same-named items in different experiments separately.

Hashes cover every field and row order. Editing text, changing a factor value,
or reordering rows changes the fingerprint. Reordering JSON object keys does not.
The fingerprint is compatible with `metadata.stimuli_sha256` in saved runs; it is
not a hash of a file's raw bytes. JSONL and CSV round trips preserve it.

Exporters validate before opening their destination, so an invalid dataset cannot
overwrite an existing materials file. Valid exports replace the requested file.
