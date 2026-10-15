from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.run_full_search_178A import _fingerprint, _input_key


def test_input_key_uses_fallback_outside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "case" / "config.xlsx"
    external.parent.mkdir()
    external.write_bytes(b"workbook")

    assert _input_key(external, root=root, fallback="case/config.xlsx") == "case/config.xlsx"


def test_fingerprint_supports_external_case_root(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    case_root = tmp_path / "case" / "178A"
    case_root.mkdir(parents=True)
    (case_root / "config.xlsx").write_bytes(b"workbook")
    victim = tmp_path / "external" / "victim.s4p"
    victim.parent.mkdir()
    victim.write_bytes(b"touchstone")
    cfg = SimpleNamespace(
        channel=SimpleNamespace(
            victim_s4p_path=str(victim),
            next_s4p_paths=[],
            fext_s4p_paths=[],
        )
    )

    result = _fingerprint(case_root, cfg)

    assert set(result) == {"case/config.xlsx", "channel/victim/000/victim.s4p"}
    assert all(len(digest) == 64 for digest in result.values())
    assert _input_key(root / "README.md", root=root, fallback="unused") == "README.md"
