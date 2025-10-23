from spagettypy.analyzer.graph.networkx_facade import GraphX

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
