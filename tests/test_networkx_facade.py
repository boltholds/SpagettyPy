from spagettypy.analyzer.graph.networkx_facade import GraphX
from spagettypy.analyzer.model import Relation, FileInfo
from pathlib import Path

def test_graph_add_and_iter_nodes_edges():
    g = GraphX[str, dict]()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B", data={"weight": 1})

    assert g.has_node("A")
    assert g.has_edge("A", "B")

    nodes = list(g.nodes())
    edges = list(g.edges())

    assert ("A", "B", {"weight": 1}) in edges
    assert "A" in nodes and "B" in nodes
    assert len(g) == 2

def test_graph_children_and_parents():
    g = GraphX[str, None]()
    g.add_edge("parent", "child")

    assert list(g.children("parent")) == ["child"]
    assert list(g.parents("child")) == ["parent"]

def test_subgraph_contains_subset():
    g = GraphX[str, None]()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    sub = g.subgraph(["A", "B"])
    assert "C" not in sub
    assert sub.has_edge("A", "B")

def test_repr_and_contains():
    g = GraphX[int, None]()
    g.add_node(1)
    assert "nodes" in repr(g)
    assert 1 in g


# ───────────────────────────────
# remove_node / remove_edge
# ───────────────────────────────
def test_remove_node_and_edge():
    g = GraphX[str, None]()
    g.add_edge("A", "B")
    assert g.has_edge("A", "B")
    g.remove_edge("A", "B")
    assert not g.has_edge("A", "B")

    g.add_node("C")
    assert g.has_node("C")
    g.remove_node("C")
    assert not g.has_node("C")


# ───────────────────────────────
# descendants / ancestors
# ───────────────────────────────
def test_descendants_and_ancestors():
    g = GraphX[str, None]()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("A", "D")

    # Проверяем транзитивные отношения
    desc = g.descendants("A")
    anc = g.ancestors("C")

    assert "C" in desc and "D" in desc
    assert "A" in anc


# ───────────────────────────────
# get_edge_data
# ───────────────────────────────
def test_get_edge_data_returns_relation():
    g = GraphX[str, Relation]()
    g.add_edge("A", "B", data=Relation.CONTAINS)
    assert g.get_edge_data("A", "B") == Relation.CONTAINS
    assert g.get_edge_data("A", "C") is None


# ───────────────────────────────
# show_summary (проверяем stdout)
# ───────────────────────────────
def test_show_summary_prints(capsys):
    g = GraphX()
    file_a = FileInfo(name="a", format=".py", path=Path("src"))
    file_b = FileInfo(name="b", format=".py", path=Path("src"))
    g.add_edge(file_a, file_b, data=Relation.CONTAINS)

    g.show_summary()
    out = capsys.readouterr().out

    assert "Узлов" in out
    assert "Рёбер" in out
    assert "FileInfo" in out
    assert "--(Relation.CONTAINS"[:10] or "--(contains"[:10]  # в зависимости от