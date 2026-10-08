"""Phase 4: the shared transcript loader is exercised for real (a fake transcript), not only imported."""
import json

from benchmarks import _corpus


def _write(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    rows = [
        {"type": "user", "message": {"content": "  analiza las ventas  "}},
        {"type": "user", "message": {"content": "<system-reminder>x</system-reminder>"}},
        {"type": "user", "message": {"content": "/clear"}},
        {"type": "user", "message": {"content": "[tool echo]"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "hecho"}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": [{"type": "text", "text": "L1"}, {"type": "text", "text": "L2"}]}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "plain result"}]}},
    ]
    p = d / "s.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    return str(tmp_path / "*" / "*.jsonl")


def test_loader_reads_filters_and_tags(tmp_path, monkeypatch):
    monkeypatch.setenv("AIXL_TRANSCRIPTS_GLOB", _write(tmp_path))
    files = _corpus.transcript_files()
    assert len(files) == 1
    assert _corpus.real_user_messages() == {"analiza las ventas"}
    kinds = [k for k, _ in _corpus.blocks(files[0])]
    assert kinds.count("tool_result") == 2 and "assistant_text" in kinds
    assert list(_corpus.tool_results(files[0])) == ["L1\nL2", "plain result"]


def test_skip_meta_matches_the_original_real_eval_filter(tmp_path, monkeypatch):
    d = tmp_path / "proj"
    d.mkdir()
    rows = [{"type": "user", "isMeta": True, "message": {"content": "meta text"}}, {"type": "user", "message": {"content": "real text"}}]
    (d / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setenv("AIXL_TRANSCRIPTS_GLOB", str(tmp_path / "*" / "*.jsonl"))
    assert _corpus.real_user_messages() == {"meta text", "real text"}
    assert _corpus.real_user_messages(skip_meta=True) == {"real text"}
