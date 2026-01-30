"""Check that the published demo faithfully bundles the measured source runs."""

import importlib.util
import json
import re
import shutil
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from statistics import mean
from urllib.parse import unquote, urlsplit

import pytest

from scopeglass.analysis import analyze, bootstrap
from scopeglass.scorers import ToyScorer
from scopeglass.stimuli import generate

ROOT = Path(__file__).resolve().parents[1]
MODELS = ("distilgpt2", "gpt2")
ASSETS = ("index.html", "style.css", "app.js")


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("build_demo", ROOT / "scripts" / "build_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def source_runs():
    return {name: json.loads((ROOT / "examples" / f"{name}-v2" / "results.json").read_text())
            for name in MODELS}


@pytest.fixture(scope="module")
def bundle(builder, tmp_path_factory):
    output = tmp_path_factory.mktemp("demo") / "public" / "scopeglass"
    builder.build(output)
    return output


def test_build_creates_nested_output_and_copies_demo_assets(bundle):
    for asset in ASSETS:
        assert (bundle / asset).read_bytes() == (ROOT / "demo" / asset).read_bytes()
    assert (bundle / "data" / "comparison.json").is_file()
    for model in MODELS:
        assert (bundle / "data" / f"{model}.json").is_file()
        assert (bundle / f"{model}-report.html").is_file()


@pytest.mark.parametrize("model", MODELS)
def test_bundled_scores_and_provenance_agree_with_measured_source(bundle, source_runs, model):
    published = json.loads((bundle / "data" / f"{model}.json").read_text())
    source = source_runs[model]
    assert published["rows"] == source["rows"]
    assert published["metadata"] == source["metadata"]
    assert published["metadata"]["empirical"] is True
    assert published["analysis"] == source["analysis"]
    assert published["summary"] == analyze(source["rows"], **source["analysis"])

    report = (bundle / f"{model}-report.html").read_text()
    payload = re.search(r'<script id="run-data" type="application/json">(.*?)</script>',
                        report, re.S)
    assert payload is not None
    assert json.loads(payload.group(1)) == published


def test_published_comparison_pairs_measured_contrasts_in_correct_direction(bundle, source_runs):
    comparison = json.loads((bundle / "data" / "comparison.json").read_text())
    left, right = (source_runs[model] for model in MODELS)
    summaries = [{result["key"]: result for result in run["summary"]} for run in (left, right)]
    assert comparison["direction"] == "right_minus_left"
    assert comparison["metadata"] == {"left": left["metadata"], "right": right["metadata"]}
    assert {result["key"] for result in comparison["summary"]} == set(summaries[0])
    for result in comparison["summary"]:
        a, b = (summary[result["key"]] for summary in summaries)
        left_items = {item["item"]: item["value"] for item in a["items"]}
        expected = [{"item": item["item"], "left": left_items[item["item"]],
                     "right": item["value"], "delta": item["value"] - left_items[item["item"]]}
                    for item in b["items"]]
        deltas = [item["delta"] for item in expected]
        assert result["items"] == expected
        assert result["estimate"] == pytest.approx(mean(deltas))
        assert result["ci95"] == bootstrap(deltas, **comparison["analysis"])


def test_generated_landing_page_has_no_broken_local_asset_or_download_links(bundle):
    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []
            self.ids = set()

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            self.ids.update([attrs["id"]] if "id" in attrs else [])
            self.urls.extend(attrs[key] for key in ("src", "href") if key in attrs)

    page = Links()
    page.feed((bundle / "index.html").read_text())
    local_paths = set()
    for link in page.urls:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        if not parsed.path:
            assert parsed.fragment in page.ids
            continue
        path = bundle / unquote(parsed.path)
        if path.is_dir():
            path = path / "index.html"
        assert path.is_file(), f"Broken demo link: {link}"
        local_paths.add(path.relative_to(bundle).as_posix())
    assert {"style.css", "app.js", "distilgpt2-report.html",
            "data/distilgpt2.json"} <= local_paths


def temporary_sources(path, runs):
    (path / "demo").mkdir(parents=True)
    for asset in ASSETS:
        shutil.copyfile(ROOT / "demo" / asset, path / "demo" / asset)
    for name, run in runs.items():
        folder = path / "examples" / f"{name}-v2"
        folder.mkdir(parents=True)
        (folder / "results.json").write_text(json.dumps(run))
    return path


def test_build_recomputes_stale_summaries_without_changing_sources(
    builder, source_runs, tmp_path, monkeypatch,
):
    altered = deepcopy(source_runs)
    for run in altered.values():
        run["summary"] = [{"key": "stale", "estimate": 999}]
        run["analysis"] = {"samples": 10, "seed": 3}
    source_root = temporary_sources(tmp_path / "sources", altered)
    monkeypatch.setattr(builder, "ROOT", source_root)
    output = tmp_path / "published"
    builder.build(output)
    for name, original in altered.items():
        source_file = source_root / "examples" / f"{name}-v2" / "results.json"
        assert json.loads(source_file.read_text()) == original
        published = json.loads((output / "data" / f"{name}.json").read_text())
        assert published["summary"] == analyze(original["rows"], **original["analysis"])


def test_public_demo_rejects_toy_scores(builder, tmp_path, monkeypatch):
    scorer = ToyScorer()
    run = {
        "schema_version": 1, "metadata": dict(scorer.metadata),
        "analysis": {"samples": 2, "seed": 17},
        "rows": [{**row.to_dict(), **scorer.score(row)} for row in generate("np_s")],
    }
    source_root = temporary_sources(tmp_path / "sources", {name: run for name in MODELS})
    monkeypatch.setattr(builder, "ROOT", source_root)
    output = tmp_path / "published"
    with pytest.raises(ValueError, match="must use measured runs"):
        builder.build(output)
    assert not (output / "data" / "distilgpt2.json").exists()
