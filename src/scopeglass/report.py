import json
from importlib.resources import files
from pathlib import Path


def write_report(run: dict, output: Path):
    template = files("scopeglass").joinpath("report.html").read_text(encoding="utf-8")
    # Keep user-supplied text inside the inert JSON block, even if it contains HTML.
    payload = json.dumps(run, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__SCOPEGLASS_DATA__", payload), encoding="utf-8")
