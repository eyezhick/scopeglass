import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .analysis import analyze
from .report import write_report
from .scorers import HuggingFaceScorer, ToyScorer
from .stimuli import generate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect the grammar inside a language model")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("stimuli", help="Export the original factorial materials as JSONL")
    export.add_argument("--experiment", choices=["all", "garden_path", "agreement", "polarity"],
                        default="all")
    run = commands.add_parser("run", help="Score materials and produce JSON plus an offline report")
    run.add_argument("--backend", choices=["toy", "hf"], default="toy")
    run.add_argument("--model", default="distilbert/distilgpt2")
    run.add_argument("--revision", help="Hugging Face revision; resolved commit is recorded")
    run.add_argument("--device", default="cpu")
    run.add_argument("--threads", type=int, default=4)
    run.add_argument("--experiment", choices=["all", "garden_path", "agreement", "polarity"],
                     default="all")
    run.add_argument("--bootstrap", type=int, default=2000)
    run.add_argument("--seed", type=int, default=17)
    run.add_argument("--out", type=Path, default=Path("runs/latest"))
    report = commands.add_parser("report", help="Rebuild a report from a saved run")
    report.add_argument("input", type=Path)
    report.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stimuli":
            for row in generate(args.experiment):
                print(json.dumps(row.to_dict()))
            return
        if args.command == "report":
            data = json.loads(args.input.read_text())
            data["summary"] = analyze(data["rows"], **data["analysis"])
            write_report(data, args.out)
            return
        if args.threads < 1 or args.bootstrap < 1:
            raise ValueError("--threads and --bootstrap must be positive")
        if args.backend == "hf":
            import torch
            torch.set_num_threads(args.threads)
            scorer = HuggingFaceScorer(args.model, args.revision, args.device)
        else:
            scorer = ToyScorer()
            print("TOY ORACLE: stipulated values, not measured model behavior", file=sys.stderr)
        stimuli = generate(args.experiment)
        rows = []
        for i, row in enumerate(stimuli, 1):
            rows.append({**row.to_dict(), **scorer.score(row)})
            if i % 24 == 0:
                print(f"Scored {i}/{len(stimuli)}", file=sys.stderr)
        material = json.dumps([row.to_dict() for row in stimuli], sort_keys=True).encode()
        analysis_args = {"samples": args.bootstrap, "seed": args.seed}
        data = {
            "schema_version": 1,
            "metadata": {
                **scorer.metadata, "scopeglass": __version__, "python": platform.python_version(),
                "platform": platform.platform(),
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "stimuli_sha256": hashlib.sha256(material).hexdigest(), "threads": args.threads,
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
