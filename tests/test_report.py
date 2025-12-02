"""Exercise the offline report in Node with the small DOM surface it uses."""

import csv
import io
import json
import re
import shutil
import subprocess
from importlib.resources import files

import pytest

from scopeglass.report import write_report


@pytest.fixture
def report_run():
    rows = []
    for experiment, item, score in [("np_s", "frame1", 3), ("agreement", "frame1", 1),
                                    ("np_s", "frame2", 2)]:
        rows.append({
            "experiment": experiment, "item": item, "factors": {"condition": "test"},
            "context": "The reader knew", "target": " words", "spillover": " were useful.",
            "surprisal_bits": score, "tokens": [{"text": " words", "bits": score}],
        })
    return {"metadata": {"empirical": False, "model": "toy"}, "analysis": {},
            "summary": [], "rows": rows}


def evaluate_report(run, expression):
    """Run the shipped script; emulate DOM text/children/events, not layout."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for offline report behavior checks")
    html = files("scopeglass").joinpath("report.html").read_text()
    script = re.search(r"<script>\n(.*?)</script>", html, re.S).group(1)
    harness = r"""
class Element {
  constructor(tag = 'div', text = '') {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.listeners = {};
    this.ownText = text;
    this.classList = {add() {}};
    this.selection = undefined;
  }
  set textContent(text) { this.ownText = String(text); this.children = []; }
  get textContent() { return this.ownText + this.children.map(n => n.textContent).join(''); }
  set value(value) { this.selection = value; }
  get value() { return this.selection ?? this.firstChild?.value ?? ''; }
  get firstChild() { return this.children[0]; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; this.selection = undefined; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(event, callback) { this.listeners[event] = callback; }
  focus() { this.focused = true; }
  click() { this.listeners.click?.(); }
  remove() {}
}
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  },
  createElement: tag => new Element(tag),
  createElementNS: (_, tag) => new Element(tag),
  createTextNode: text => new Element('#text', text),
  body: new Element('body'),
};
for (const id of ['experiment', 'item']) {
  const option = new Element('option', 'All');
  option.value = 'all';
  document.getElementById(id).append(option);
}
document.getElementById('run-data').textContent = RUN;
"""
    result = subprocess.run(
        [node, "-e", "const RUN = " + json.dumps(json.dumps(run)) + ";\n" + harness
         + script + "\nconsole.log(JSON.stringify(" + expression + "));"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_run_counts_and_experiments_follow_loaded_rows(report_run):
    result = evaluate_report(
        report_run, "({overview: $('overview').textContent, "
        "options: $('experiment').children.map(o => [o.value, o.textContent])})",
    )
    assert result["overview"] == "2 experiments · 3 lexical frames · 3 scored conditions"
    assert result["options"] == [["all", "All"], ["np_s", "NP/S ambiguity"],
                                  ["agreement", "Agreement attraction"]]


def test_run_payload_round_trip_remains_inert(tmp_path):
    run = {"text": '</script><img src=x onerror="alert(1)">\u2028 & café', "rows": []}
    output = tmp_path / "report.html"
    write_report(run, output)
    html = output.read_text()
    data = re.search(r'<script id="run-data" type="application/json">(.*?)</script>', html, re.S)
    assert json.loads(data.group(1)) == run
    assert '<img src=x' not in html
    assert len(re.findall(r"<script\b", html)) == 2


def test_score_order_combines_with_filters_without_mutating_run(report_run):
    result = evaluate_report(report_run, "(() => { $('order').value = 'high'; "
                             "$('experiment').value = 'np_s'; $('search').value = ' WORDS '; "
                             "render(); return {scores: filteredRows().map(r => r.surprisal_bits), "
                             "original: run.rows.map(r => r.surprisal_bits), "
                             "count: $('count').textContent}; })()")
    assert result == {"scores": [3, 2], "original": [3, 1, 2], "count": "2 conditions"}


def test_low_score_and_natural_frame_order(report_run):
    report_run["rows"][0]["item"] = "frame10"
    result = evaluate_report(report_run, "(() => { $('order').value = 'low'; "
                             "const low = filteredRows().map(r => r.surprisal_bits); "
                             "$('order').value = 'item'; "
                             "return {low, items: filteredRows().map(r => r.item)}; })()")
    assert result == {"low": [1, 2, 3], "items": ["frame1", "frame2", "frame10"]}


def test_reset_clears_all_filters_and_returns_focus_to_search(report_run):
    result = evaluate_report(report_run, "(() => { $('experiment').value = 'np_s'; "
                             "updateItems(); $('item').value = 'frame2'; "
                             "$('search').value = 'absent'; $('order').value = 'high'; "
                             "$('reset').click(); return {count: $('count').textContent, "
                             "experiment: $('experiment').value, item: $('item').value, "
                             "query: $('search').value, order: $('order').value, "
                             "focused: $('search').focused}; })()")
    assert result == {"count": "3 conditions", "experiment": "all", "item": "all",
                      "query": "", "order": "source", "focused": True}


def test_csv_preserves_quoted_multiline_fields_and_protects_formulas(report_run):
    report_run["rows"][0].update({"context": 'A "quote", café\nsecond line',
                                  "target": " =SUM(A1:A2)", "spillover": "\t@danger"})
    exported = evaluate_report(report_run, "exportRowsCsv(run.rows)")
    records = list(csv.DictReader(io.StringIO(exported)))
    assert len(records) == 3
    assert records[0]["context"] == 'A "quote", café\nsecond line'
    assert records[0]["target"] == "' =SUM(A1:A2)"
    assert records[0]["spillover"] == "'\t@danger"
    assert records[0]["surprisal_bits"] == "3"
    assert json.loads(records[0]["tokens"]) == report_run["rows"][0]["tokens"]


def test_csv_uses_active_filters_and_order(report_run):
    exported = evaluate_report(report_run, "(() => { $('experiment').value = 'np_s'; "
                               "$('order').value = 'low'; "
                               "return exportRowsCsv(filteredRows()); })()")
    records = list(csv.DictReader(io.StringIO(exported)))
    assert [row["item"] for row in records] == ["frame2", "frame1"]
