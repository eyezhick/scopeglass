"""Exercise the offline report in Node with the small DOM surface it uses."""

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
