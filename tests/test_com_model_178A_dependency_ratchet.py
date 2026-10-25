"""Prevent expansion of the temporary 178A-to-93A dependency surface."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src" / "serdes_coding" / "models" / "com_model_178A.py"
SEARCH = ROOT / "src" / "serdes_coding" / "search" / "com_search_178A.py"


def _attributes_for_alias(path: Path, alias: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == alias
    }


def test_178a_model_does_not_expand_temporary_93a_dependencies() -> None:
    assert _attributes_for_alias(MODEL, "com_93A") == {
        "COMChannelConfig",
        "COMPMFConfig",
        "COMPMFRuntimeConfig",
        "COMPMFStatus",
        "COMPath",
        "COMSearchCandidate",
        "COMSearchConfig",
        "COMSharedPath",
        "IEEECOMFilter",
        "IEEECOMSparam",
        "_build_channel_under_test_93A",
        "_build_pmf_XT_all_93A",
        "_build_pmf_interference_93A",
        "_find_pos_xtalk_93A",
    }


def test_178a_search_does_not_expand_temporary_93a_dependencies() -> None:
    assert _attributes_for_alias(SEARCH, "com_93A") == {
        "COMSearchCandidate",
        "COMSearchConfig",
    }
