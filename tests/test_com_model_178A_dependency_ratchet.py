"""Prevent expansion of the temporary 178A-to-93A dependency surface."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "serdes_coding"
MODEL = SOURCE / "models" / "com_model_178A.py"
SEARCH = SOURCE / "search" / "com_search_178A.py"
IO_ADAPTER = SOURCE / "io" / "com_excel_io_178A.py"
OWNED_PACKAGE = SOURCE / "models" / "com_178a"
SCANNED = (MODEL, SEARCH, IO_ADAPTER, *sorted(OWNED_PACKAGE.glob("*.py")))


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _93a_imports(path: Path) -> tuple[set[str], set[str]]:
    """Return aliases bound to the 93A module and directly imported names."""
    aliases: set[str] = set()
    direct: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name.endswith("com_model_93A"):
                    aliases.add(item.asname or item.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith("com_model_93A"):
                direct.update(item.name for item in node.names)
            elif any(item.name == "com_model_93A" for item in node.names):
                aliases.update(
                    item.asname or item.name
                    for item in node.names
                    if item.name == "com_model_93A"
                )
    return aliases, direct


def _dynamic_93a_imports(path: Path) -> set[str]:
    """Find literal dynamic imports that target the 93A model module."""
    targets: set[str] = set()
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        is_import_module = (
            isinstance(function, ast.Attribute) and function.attr == "import_module"
        ) or (isinstance(function, ast.Name) and function.id == "import_module")
        first = node.args[0]
        if (
            is_import_module
            and isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and "com_model_93A" in first.value
        ):
            targets.add(first.value)
    return targets


def _attributes_for_aliases(path: Path, aliases: set[str]) -> set[str]:
    return {
        node.attr
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in aliases
    }


def test_only_178a_model_retains_an_explicit_93a_import() -> None:
    imports = {path: _93a_imports(path) for path in SCANNED}
    importers = {
        path.relative_to(ROOT).as_posix(): dependency
        for path, dependency in imports.items()
        if any(dependency)
    }
    model_key = MODEL.relative_to(ROOT).as_posix()
    assert set(importers) == {model_key}
    aliases, direct = importers[model_key]
    assert aliases == {"com_93A"}
    assert direct == set()
    assert all(_dynamic_93a_imports(path) == set() for path in SCANNED)


def test_178a_model_does_not_expand_temporary_93a_dependencies() -> None:
    aliases, _ = _93a_imports(MODEL)
    assert _attributes_for_aliases(MODEL, aliases) == {
        "_build_pmf_XT_all_93A",
        "_build_pmf_interference_93A",
        "_find_pos_xtalk_93A",
    }
