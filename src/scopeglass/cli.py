import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .analysis import analyze
from .materials import (
    describe_materials,
    load_csv,
    load_jsonl,
    material_hash,
    validate_materials,
    write_csv,
    write_jsonl,
)
from .report import write_report
from .scorers import HuggingFaceScorer, ToyScorer
from .stimuli import generate

EXPERIMENTS = ["all", "garden_path", "np_s", "agreement", "polarity"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect the grammar inside a language model")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("stimuli", help="Export the original factorial materials as JSONL")
    export.add_argument("--experiment", choices=EXPERIMENTS,
                        default="all")
    export.add_argument("--out", type=Path, help="Write JSONL or CSV, chosen by file suffix")
    inspect = commands.add_parser("validate", help="Inspect a complete JSONL or CSV design")
    inspect.add_argument("input", type=Path)
    run = commands.add_parser("run", help="Score materials and produce JSON plus an offline report")
    run.add_argument("--backend", choices=["toy", "hf"], default="toy")
    run.add_argument("--model", default="distilbert/distilgpt2")
    run.add_argument("--revision", help="Hugging Face revision; resolved commit is recorded")
    run.add_argument("--device", default="cpu")
    run.add_argument("--threads", type=int, default=4)
    run.add_argument("--experiment", choices=EXPERIMENTS,
                     default="all")
    run.add_argument("--bootstrap", type=int, default=2000)
    run.add_argument("--seed", type=int, default=17)
    run.add_argument("--out", type=Path, default=Path("runs/latest"))
    run.add_argument("--materials", type=Path, help="Custom full-frame JSONL or CSV materials")
    report = commands.add_parser("report", help="Rebuild a report from a saved run")
    report.add_argument("input", type=Path)
    report.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stimuli":
            rows = generate(args.experiment)
            if args.out:
                writer = write_csv if args.out.suffix.lower() == ".csv" else write_jsonl
                writer(rows, args.out)
            else:
                for row in rows:
                    print(json.dumps(row.to_dict()))
            return
        if args.command == "validate":
            loader = load_csv if args.input.suffix.lower() == ".csv" else load_jsonl
            print(json.dumps(describe_materials(loader(args.input)), indent=2))
            return
        if args.command == "report":
            data = json.loads(args.input.read_text())
            data["summary"] = analyze(data["rows"], **data["analysis"])
            write_report(data, args.out)
            return
        if args.threads < 1 or args.bootstrap < 1:
            raise ValueError("--threads and --bootstrap must be positive")
        if args.materials:
            loader = load_csv if args.materials.suffix.lower() == ".csv" else load_jsonl
            stimuli = loader(args.materials)
            if args.experiment != "all":
                stimuli = [row for row in stimuli if row.experiment == args.experiment]
        else:
            stimuli = generate(args.experiment)
        validate_materials(stimuli)
        if args.backend == "hf":
            import torch
            torch.set_num_threads(args.threads)
            scorer = HuggingFaceScorer(args.model, args.revision, args.device)
        else:
            scorer = ToyScorer()
            print("TOY ORACLE: stipulated values, not measured model behavior", file=sys.stderr)
        rows = []
        for i, row in enumerate(stimuli, 1):
            rows.append({**row.to_dict(), **scorer.score(row)})
            if i % 24 == 0:
                print(f"Scored {i}/{len(stimuli)}", file=sys.stderr)
        analysis_args = {"samples": args.bootstrap, "seed": args.seed}
        data = {
            "schema_version": 1,
            "metadata": {
                **scorer.metadata, "scopeglass": __version__, "python": platform.python_version(),
                "platform": platform.platform(),
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "stimuli_sha256": material_hash(stimuli), "threads": args.threads,
                "experiment": args.experiment,
            },
            "analysis": analysis_args, "summary": analyze(rows, **analysis_args), "rows": rows,
        }
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "results.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
        write_report(data, args.out / "report.html")
        for result in data["summary"]:
            lo, hi = result["ci95"]
            print(f"{result['title']}: {result['estimate']:+.3f} bits [{lo:+.3f}, {hi:+.3f}]")
        print(f"Report: {args.out / 'report.html'}")
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"scopeglass: {exc}\n")


if __name__ == "__main__":
    main()
