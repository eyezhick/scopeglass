"""Render the README figures from checked-in model runs.

Run from any directory with a Python environment containing matplotlib:
    python scripts/render_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets"
PAPER, INK, MUTED, GRID = "#f6f3ea", "#1d302b", "#59665f", "#d5dacd"
MODELS = (
    ("distilgpt2", "DistilGPT-2", "#14634f", "o", 0.14),
    ("gpt2", "GPT-2", "#ae452b", "D", -0.14),
)


def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "axes.facecolor": PAPER,
        "figure.facecolor": PAPER,
        "xtick.color": MUTED,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "scopeglass-figures-v1",
        "savefig.dpi": 180,
    })


def load_runs():
    runs = {}
    for key, *_ in MODELS:
        path = ROOT / "examples" / f"{key}-v2" / "results.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        if run["metadata"].get("empirical") is not True:
            raise ValueError(f"Figure requires measured model output: {path}")
        runs[key] = run
    return runs


def heading(fig, kicker, title, subtitle):
    fig.text(.045, .95, kicker, color=MUTED, size=10, fontfamily="DejaVu Sans Mono")
    fig.text(.045, .89, title, size=27, fontfamily="DejaVu Serif")
    fig.text(.045, .845, subtitle, size=11.5, color=MUTED)


def legend(fig, y):
    handles = [
        Line2D([], [], color=color, marker=marker, markersize=7, linewidth=2, label=name)
        for _, name, color, marker, _ in MODELS
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.04, y),
               frameon=False, ncols=2, columnspacing=2.2, handlelength=2)


def save(fig, name, title):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", metadata={"Software": "Scopeglass"})
    fig.savefig(OUTPUT / f"{name}.svg", metadata={
        "Title": title, "Date": None, "Creator": "Scopeglass",
        "Description": "Measured results from the two checked-in Scopeglass v2 model runs.",
    })
    plt.close(fig)


def effects_overview(runs):
    contrasts = (
        ("np_s", "NP/S · complementizer interaction"),
        ("garden_path", "NP/Z · comma interaction"),
        ("agreement_margin", "Agreement preference"),
        ("attraction", "Attraction penalty"),
        ("matrix_licensing", "Matrix negation benefit"),
        ("embedded_licensing", "Embedded negation benefit"),
        ("scope_selectivity", "Scope selectivity"),
    )
    fig = plt.figure(figsize=(13.5, 8.3))
    heading(fig, "SCOPEGLASS / MEASURED EFFECTS", "Seven contrasts. Two models.",
            "Signed within-frame effects across twelve authored lexical frames per contrast.")
    legend(fig, .81)
    ax = fig.add_axes((.34, .205, .60, .535))
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID, linewidth=.7)
    ax.axvline(0, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
    for position in (4.5, 2.5):
        ax.axhline(position, color=GRID, linewidth=.8)
    for key, _, color, marker, offset in MODELS:
        results = {row["key"]: row for row in runs[key]["summary"]}
        for index, (contrast, _) in enumerate(contrasts):
            result = results[contrast]
            if result["n_items"] != 12:
                raise ValueError("Overview caption expects twelve frames per contrast")
            low, high = result["ci95"]
            y = 6 - index + offset
            ax.plot([low, high], [y, y], color=color, linewidth=2.3,
                    solid_capstyle="round")
            ax.scatter(result["estimate"], y, s=46, color=color, marker=marker,
                       edgecolors=PAPER, linewidths=.7, zorder=3)
    ax.set_yticks(range(6, -1, -1), [label for _, label in contrasts], fontsize=11.5)
    ax.tick_params(axis="y", length=0, pad=17)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.set_ylim(-.55, 6.55)
    ax.set_xlim(-12, 14)
    ax.set_xticks(range(-12, 15, 2))
    ax.set_xlabel("Within-frame contrast (bits)", labelpad=13)
    fig.text(.045, .102,
             "Points: mean contrast. Lines: 95% item-bootstrap intervals; "
             "2,000 resamples, seed 17; n = 12 frames.", size=10.5, color=MUTED)
    fig.text(.045, .063,
             "Signs follow each contrast’s definition; a larger value is not uniformly better.",
             size=10.5, color=MUTED)
    fig.text(.955, .022, "Source: examples/{distilgpt2-v2,gpt2-v2}/results.json",
             ha="right", size=8.5, color=MUTED)
    save(fig, "effects-overview", "Seven signed linguistic contrasts in two language models")


def ambiguity_conditions(runs):
    panels = (
        ("garden_path", "npz-00", "comma", "NP/Z · npz-00 · target: ran",
         "While the hunter hunted the deer ran into the woods.",
         ["hunted · no comma", "hunted · comma", "slept · no comma", "slept · comma"],
         19.5, [0, 5, 10, 15]),
        ("np_s", "nps-00", "that", "NP/S · nps-00 · target: was",
         "The editor knew the author was exhausted.",
         ["knew · no that", "knew · that", "insisted · no that", "insisted · that"],
         3.35, [0, 1, 2, 3]),
    )
    fig = plt.figure(figsize=(14, 8.4))
    heading(fig, "SCOPEGLASS / TWO LEXICAL FRAMES", "Read the conditions before the average.",
            "Critical-region surprisal. Lower values mean the scored region was more expected.")
    legend(fig, .81)
    for column, panel in enumerate(panels):
        experiment, item, cue, title, sentence, labels, maximum, ticks = panel
        left = .185 + column * .48
        ax = fig.add_axes((left, .29, .29, .36))
        fig.text(left - .14, .72, title, size=11, fontweight="bold")
        fig.text(left - .14, .684, sentence, size=10, color=MUTED, fontstyle="italic")
        cells = [(ambiguity, boundary)
                 for ambiguity in ("ambiguous", "control") for boundary in ("absent", cue)]
        ax.set_axisbelow(True)
        ax.grid(axis="x", color=GRID, linewidth=.7)
        ax.axhline(1.5, color=GRID, linewidth=.8)
        interaction_text = []
        for key, name, color, marker, offset in MODELS:
            rows = [row for row in runs[key]["rows"]
                    if row["experiment"] == experiment and row["item"] == item]
            values = {(row["factors"]["ambiguity"], row["factors"]["boundary"]):
                      row["surprisal_bits"] for row in rows}
            for index, cell in enumerate(cells):
                y = 3 - index + offset
                value = values[cell]
                ax.barh(y, value, height=.23, color=color, alpha=.92)
                ax.scatter(value, y, marker=marker, color=color, s=18, zorder=3)
                ax.text(value + maximum * .025, y, f"{value:.2f}", va="center",
                        fontsize=9, color=color)
            interaction = values[cells[0]] - values[cells[1]] - values[cells[2]] + values[cells[3]]
            interaction_text.append((name, interaction, color))
        ax.set_yticks(range(3, -1, -1), labels, fontsize=10)
        ax.tick_params(axis="y", length=0, pad=12)
        ax.tick_params(axis="x", length=0, pad=8)
        ax.set_ylim(-.55, 3.55)
        ax.set_xlim(0, maximum)
        ax.set_xticks(ticks)
        ax.set_xlabel("Critical-region surprisal (bits)", labelpad=12, fontsize=10)
        fig.text(left - .14, .187, "This frame’s interaction", size=10, color=MUTED)
        for index, (name, value, color) in enumerate(interaction_text):
            fig.text(left - .14 + index * .24, .153, f"{name}  {value:+.2f} bits",
                     color=color, size=11, fontweight="bold")
    fig.text(.045, .087,
             "Interaction = (ambiguous, no cue − ambiguous, cue) "
             "− (control, no cue − control, cue).", size=10, color=MUTED)
    fig.text(.045, .049,
             "Panel scales differ. These are individual frames, not corpus means; "
             "no uncertainty interval is shown.", size=10, color=MUTED)
    fig.text(.955, .014, "Source: examples/{distilgpt2-v2,gpt2-v2}/results.json",
             ha="right", size=8.5, color=MUTED)
    save(fig, "ambiguity-conditions", "Four controlled conditions in each of two ambiguity frames")


if __name__ == "__main__":
    setup()
    measured_runs = load_runs()
    for run in measured_runs.values():
        if run["analysis"] != {"samples": 2000, "seed": 17}:
            raise ValueError("Figure captions expect 2,000 bootstrap resamples with seed 17")
    effects_overview(measured_runs)
    ambiguity_conditions(measured_runs)
