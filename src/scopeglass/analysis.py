"""Within-item contrasts, with a paired bootstrap over lexical frames."""

import math
import random
from collections import defaultdict
from itertools import product
from statistics import mean

DESIGNS = {
    "garden_path": (("ambiguity", "boundary"), (("ambiguous", "control"), ("absent", "comma"))),
    "agreement": (("head", "distractor", "verb"), (("sg", "pl"),) * 3),
    "polarity": (
        ("location", "negation", "target"),
        (("matrix", "embedded"), ("absent", "present"), ("npi", "control")),
    ),
}

LABELS = {
    "garden_path": (
        "Garden-path interaction",
        "Positive: the missing-comma cost is larger after the ambiguous verb.",
    ),
    "agreement_margin": (
        "Agreement preference",
        "Positive: the grammatical verb is preferred, averaged across all four contexts.",
    ),
    "attraction": (
        "Attraction penalty",
        "Positive: a mismatching distractor weakens preference for the grammatical verb.",
    ),
    "matrix_licensing": (
        "Matrix licensing benefit",
        "Positive: matrix negation favors ever over often, relative to the positive control.",
    ),
    "embedded_licensing": (
        "Embedded negation benefit",
        "Positive: embedded negation also favors ever; it is outside the intended licensing scope.",
    ),
    "scope_selectivity": (
        "Scope selectivity",
        "Positive: matrix negation favors ever more than embedded negation does.",
    ),
}


def bootstrap(values: list[float], samples=2000, seed=17) -> list[float]:
    if not values or samples < 1:
        raise ValueError("Bootstrap requires observations and a positive sample count")
    rng = random.Random(seed)
    draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(samples))

    def quantile(p):
        position = (len(draws) - 1) * p
        lo = int(position)
        hi = min(lo + 1, len(draws) - 1)
        return draws[lo] + (draws[hi] - draws[lo]) * (position - lo)

    return [quantile(.025), quantile(.975)]


def analyze(rows: list[dict], samples=2000, seed=17) -> list[dict]:
    if not rows:
        raise ValueError("No scored rows")
    groups = defaultdict(dict)
    seen_ids = set()
    for row in rows:
        if row["id"] in seen_ids:
            raise ValueError(f"Duplicate stimulus id: {row['id']}")
        seen_ids.add(row["id"])
        experiment = row["experiment"]
        if experiment not in DESIGNS:
            raise ValueError(f"Unknown experiment: {experiment}")
        fields, levels = DESIGNS[experiment]
        if set(row["factors"]) != set(fields):
            raise ValueError(f"Unexpected factors in {row['id']}")
        cell = tuple(row["factors"][name] for name in fields)
        group = groups[(experiment, row["item"])]
        if cell in group:
            raise ValueError(f"Duplicate cell in {row['item']}: {cell}")
        value = row["surprisal_bits"]
        if not math.isfinite(value) or value < 0:
            raise ValueError("Surprisal must be finite and nonnegative")
        group[cell] = value

    contrasts = defaultdict(list)

    def add(key, item, value):
        contrasts[key].append({"item": item, "value": value})

    for (experiment, item), s in sorted(groups.items()):
        if set(s) != set(product(*DESIGNS[experiment][1])):
            raise ValueError(f"Incomplete or invalid factorial design for {item}")
        if experiment == "garden_path":
            cost = lambda verb: s[verb, "absent"] - s[verb, "comma"]  # noqa: E731
            add("garden_path", item, cost("ambiguous") - cost("control"))
        elif experiment == "agreement":
            margins = {}
            for head, distractor in product(("sg", "pl"), repeat=2):
                wrong = "pl" if head == "sg" else "sg"
                margins[head, distractor] = s[head, distractor, wrong] - s[head, distractor, head]
            add("agreement_margin", item, mean(margins.values()))
            add("attraction", item, mean([
                margins["sg", "sg"] - margins["sg", "pl"],
                margins["pl", "pl"] - margins["pl", "sg"],
            ]))
        else:
            benefits = {}
            for location in ("matrix", "embedded"):
                def preference(negation):
                    return s[location, negation, "control"] - s[location, negation, "npi"]
                benefits[location] = preference("present") - preference("absent")
                add(f"{location}_licensing", item, benefits[location])
            add("scope_selectivity", item, benefits["matrix"] - benefits["embedded"])

    results = []
    for key, (title, interpretation) in LABELS.items():
        if key not in contrasts:
            continue
        items = contrasts[key]
        values = [item["value"] for item in items]
        results.append({
            "key": key, "title": title, "interpretation": interpretation,
            "estimate": mean(values), "ci95": bootstrap(values, samples, seed),
            "n_items": len(values), "items": items,
        })
    return results
