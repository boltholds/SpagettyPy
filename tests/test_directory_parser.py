import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from spagettypy.analyzer.parsers.directory_parser import (
    GitFinder, GitignoreFileChecker, GitExcludeFileChecker,
    FormatFileChecker, DirectoryParser
)
from spagettypy.analyzer.model import FileInfo, DirectoryNode
from spagettypy.analyzer.graph.networkx_facade import GraphX

# ────────────────────────────────
# Fake pygit2 для изоляции теста
# ────────────────────────────────
class FakeRepo:
    def __init__(self, ignored=False):
        self._ignored = ignored
    def path_is_ignored(self, path): return self._ignored

@patch("spagettypy.analyzer.parsers.directory_parser.pygit2")
def test_gitfinder_and_ignorechecker(mock_pygit2, tmp_path):
    mock_pygit2.discover_repository.return_value = tmp_path / ".git"
    mock_pygit2.Repository.return_value = FakeRepo(ignored=False)

    checker = GitignoreFileChecker(tmp_path)
    f = FileInfo(name="a", format=".py", path=tmp_path)
    assert checker(f)

@patch("spagettypy.analyzer.parsers.directory_parser.pygit2")
def test_git_exclude_checker(mock_pygit2, tmp_path):
    repo_path = tmp_path / ".git"
    (repo_path / "info").mkdir(parents=True)
    (repo_path / "info" / "exclude").write_text("*.py")
    mock_pygit2.discover_repository.return_value = repo_path
    mock_pygit2.Repository.return_value = FakeRepo(ignored=True)

    checker = GitExcludeFileChecker(tmp_path)
    f = FileInfo(name="test", format=".py", path=tmp_path)
    assert checker(f)

def test_format_file_checker_single_and_multi():
    f = FileInfo(name="main", format=".py", path=Path("."))
    single = FormatFileChecker(".py")
    multi = FormatFileChecker([".txt", "py"])
    assert single(f)
    assert multi(f)

def test_directory_parser_builds_graph(tmp_path):
    d1 = tmp_path / "dir"
    d1.mkdir()
    (d1 / "a.py").write_text("print(1)")
    (d1 / "b.txt").write_text("ok")

    parser = DirectoryParser(base_path=tmp_path)

    def fake_walk(p):
        for dirpath, _, files in [(d1, [], ["a.py", "b.txt"])]:
            yield dirpath, [], files
    Path.walk = fake_walk

    g = GraphX()
    g2 = parser(g, tmp_path)

    edge_targets = [v for _, v, _ in g2.edges()]
    filenames = [getattr(v, "name", None) + getattr(v, "format", "") for v in edge_targets if hasattr(v, "format")]
    assert "a.py" in filenames
    assert "b.txt" in filenames

