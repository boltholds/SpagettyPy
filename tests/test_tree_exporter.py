from spagettypy.analyzer.exporters.tree_exporter import TreeExporter
from spagettypy.analyzer.graph.networkx_facade import GraphX

def test_tree_exporter_builds_simple_tree(capsys):
    g = GraphX[str, None]()
    g.add_edge("root", "folder")
    g.add_edge("folder", "file.txt")

    exporter = TreeExporter(root="root")
    output = exporter(g)
    assert "file.txt" in output
    assert "folder" in output
    assert "files" in output and "directories" in output

def test_tree_exporter_skips_dot_nodes():
    g = GraphX[str, None]()
    g.add_edge(".", "ignored.txt")

    exp = TreeExporter()
    out = exp(g)
    # Проверяем, что файл попал в дерево
    assert "ignored.txt" in out

    # Проверяем, что символ "." нигде не напечатан как отдельный узел
    lines = [line.strip() for line in out.splitlines()]
    assert not any(line.endswith(".") or line.strip() == "." for line in lines)
