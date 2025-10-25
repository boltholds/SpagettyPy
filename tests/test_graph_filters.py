import pytest
from spagettypy.analyzer.graph.filters import (
    BaseTypeFilter,
    FilterNodeByClass,
    FilterEdgeByClass,
    FilterEdgeByRelations,
)
from spagettypy.analyzer.graph.networkx_facade import GraphX
from spagettypy.analyzer.model import Relation


# ───────────────────────────────
# Подготовим простой граф
# ───────────────────────────────
class DummyA: ...
class DummyB: ...


@pytest.fixture
def simple_graph():
    g = GraphX()
    a, b, c = DummyA(), DummyB(), DummyA()
    g.add_edge(a, b, data=Relation.CONTAINS)
    g.add_edge(b, c, data=Relation.IMPORTS)
    return g, a, b, c


# ───────────────────────────────
# BaseTypeFilter.match
# ───────────────────────────────
def test_base_type_filter_match():
    f = BaseTypeFilter(int)
    assert f.match(5)
    assert not f.match("not int")

    f_multi = BaseTypeFilter([int, str])
    assert f_multi.match("hello")
    assert not f_multi.match(3.14)


# ───────────────────────────────
# FilterNodeByClass
# ───────────────────────────────
def test_filter_node_by_class_include(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterNodeByClass(DummyA)
    nodes = list(filt(g))
    # должны попасть все экземпляры DummyA
    assert any(isinstance(n, DummyA) for n in nodes)
    assert all(isinstance(n, (DummyA, DummyB)) for n in [a, b, c])


def test_filter_node_by_class_exclude(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterNodeByClass(DummyA, include=False)
    nodes = list(filt(g))
    # теперь должны попасть только не DummyA
    assert all(not isinstance(n, DummyA) for n in nodes)


# ───────────────────────────────
# FilterEdgeByClass
# ───────────────────────────────
def test_filter_edge_by_class_include(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterEdgeByClass(DummyA)
    edges = list(filt(g))
    # только рёбра, где обе вершины DummyA
    for u, v, _ in edges:
        assert isinstance(u, DummyA) and isinstance(v, DummyA)


def test_filter_edge_by_class_exclude(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterEdgeByClass(DummyA, include=False)
    edges = list(filt(g))
    # рёбра, где хотя бы одна вершина не DummyA
    for u, v, _ in edges:
        assert not (isinstance(u, DummyA) and isinstance(v, DummyA))


# ───────────────────────────────
# FilterEdgeByRelations
# ───────────────────────────────
def test_filter_edge_by_relations_include(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterEdgeByRelations([Relation.CONTAINS, Relation.IMPORTS])
    edges = list(filt(g))
    assert any(data in (Relation.CONTAINS, Relation.IMPORTS) for _, _, data in edges)


def test_filter_edge_by_relations_exclude(simple_graph):
    g, a, b, c = simple_graph
    filt = FilterEdgeByRelations([Relation.CONTAINS], include=False)
    edges = list(filt(g))
    assert all(data != Relation.CONTAINS for _, _, data in edges)
