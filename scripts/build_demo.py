"""Bundle the live demo from checked-in measured results; no network or inference."""

import argparse
import json
import shutil
from pathlib import Path

from scopeglass.analysis import analyze
from scopeglass.compare import compare_runs, validate_run
from scopeglass.report import write_report

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    (output / "data").mkdir(exist_ok=True)
    for asset in ("index.html", "style.css", "app.js"):
        source = ROOT / "demo" / asset
        target = output / asset
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
    runs = {}
    for name in ("distilgpt2", "gpt2"):
        data = json.loads((ROOT / "examples" / f"{name}-v2" / "results.json").read_text())
        validate_run(data)
        data["summary"] = analyze(data["rows"], **data["analysis"])
        if not data["metadata"]["empirical"]:
            raise ValueError("The public demo must use measured runs")
        (output / "data" / f"{name}.json").write_text(
            json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8",
        )
        write_report(data, output / f"{name}-report.html")
        runs[name] = data
    comparison = compare_runs(runs["distilgpt2"], runs["gpt2"])
    (output / "data" / "comparison.json").write_text(
        json.dumps(comparison, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "demo")
    args = parser.parse_args()
    build(args.out)
    print(f"Built offline data and reports in {args.out}")
