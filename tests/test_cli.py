import json

from scopeglass.cli import main
from scopeglass.report import write_report


def test_offline_run_and_report_round_trip(tmp_path):
    main(["run", "--out", str(tmp_path), "--bootstrap", "10"])
    result = json.loads((tmp_path / "results.json").read_text())
    assert len(result["rows"]) == 240
    assert len(result["summary"]) == 6
    assert not result["metadata"]["empirical"]
    main(["report", str(tmp_path / "results.json"), "--out", str(tmp_path / "again.html")])
    assert (tmp_path / "again.html").read_text() == (tmp_path / "report.html").read_text()


def test_report_cannot_break_out_of_json_script(tmp_path):
    output = tmp_path / "unsafe.html"
    write_report({"text": "</script><script>alert(1)</script>"}, output)
    assert "</script><script>alert(1)" not in output.read_text()
    assert "\\u003c/script>" in output.read_text()
