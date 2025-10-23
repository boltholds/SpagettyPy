from spagettypy.analyzer.exporters.tree_exporter import TreeDirectoryExporter
from spagettypy.analyzer.graph.networkx_facade import GraphX

def test_tree_exporter_builds_simple_tree(capsys):
    g = GraphX[str, None]()
    g.add_edge("root", "folder")
    g.add_edge("folder", "file.txt")

    exporter = TreeDirectoryExporter(root="root")
    output = exporter(g)
    assert "file.txt" in output
    assert "folder" in output
    assert "files" in output and "directories" in output

def test_tree_exporter_skips_dot_nodes():
    g = GraphX[str, None]()
    g.add_edge(".", "ignored.txt")

    exp = TreeDirectoryExporter()
    out = exp(g)
    assert "ignored.txt" in out
    assert ".txt" not in out.splitlines()[0]
