import pytest
from pathlib import Path
from spagettypy.analyzer.graph.finders import FindNodeByName, FindNodeByImportLike
from spagettypy.analyzer.graph.networkx_facade import GraphX


# ───────────────────────────────
# Вспомогательные типы
# ───────────────────────────────
class DummyNode:
    def __init__(self, name, path=None):
        self.name = name
        self.path = Path(path) if path else None


@pytest.fixture
def graph_with_nodes(tmp_path):
    g = GraphX()
    root = tmp_path
    # структура проекта: root/pkg/sub/module.py
    pkg = root / "pkg" / "sub"
    pkg.mkdir(parents=True)
    (pkg / "module.py").write_text("x=1")

    # узлы
    n1 = DummyNode("module", path=pkg)
    n2 = DummyNode("other", path=root / "other")
    n3 = DummyNode("broken", path=None)  # без пути
    n4 = DummyNode("foreign", path=Path("/external/path"))  # вне root

    for n in [n1, n2, n3, n4]:
        g.add_node(n)

    return g, root, [n1, n2, n3, n4]


# ───────────────────────────────
# FindNodeByName
# ───────────────────────────────
def test_find_node_by_name_found(graph_with_nodes):
    g, root, (n1, n2, *_ ) = graph_with_nodes
    finder = FindNodeByName(g)
    assert finder("module") == n1
    assert finder("other") == n2


def test_find_node_by_name_not_found(graph_with_nodes):
    g, root, *_ = graph_with_nodes
    finder = FindNodeByName(g)
    assert finder("missing") is None


# ───────────────────────────────
# FindNodeByImportLike._import_path_of
# ───────────────────────────────
def test_import_path_of_inside_root(graph_with_nodes):
    g, root, (n1, *_ ) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    ipath = finder._import_path_of(n1)
    # путь должен быть в виде pkg.sub.module
    assert ipath.endswith("pkg.sub.module")


def test_import_path_of_outside_root(graph_with_nodes):
    g, root, (*_, n4) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    # foreign.path вне root → должно вернуть None
    assert finder._import_path_of(n4) is None


def test_import_path_of_without_attrs(graph_with_nodes):
    g, root, (_, _, n3, _) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    assert finder._import_path_of(n3) is None


# ───────────────────────────────
# FindNodeByImportLike.__call__
# ───────────────────────────────
def test_find_node_by_import_like_full_match(graph_with_nodes):
    g, root, (n1, *_ ) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    result = finder("pkg.sub.module")
    assert result == n1


def test_find_node_by_import_like_partial_match(graph_with_nodes):
    g, root, (n1, *_ ) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    result = finder("module")  # укороченный путь
    assert result == n1


def test_find_node_by_import_like_not_found(graph_with_nodes):
    g, root, (n1, *_ ) = graph_with_nodes
    finder = FindNodeByImportLike(g, root)
    # даже если префикс неверный, совпадение по имени должно вернуть n1
    result = finder("nonexistent.module")
    assert result == n1

