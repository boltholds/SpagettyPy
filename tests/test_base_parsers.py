import ast
import pytest
from pathlib import Path
from types import SimpleNamespace

from spagettypy.analyzer.parsers.base import (
    BaseResolver,
    FactoryCodeSpan,
    AttributeFactory,
    AnalyzerBase,
    Scope,
    SymbolRepository,
)
from spagettypy.analyzer.model import CodeSpan, ImportScope


# ───────────────────────────────
# BaseResolver
# ───────────────────────────────
def test_base_resolver_resolve_and_classifier(monkeypatch):
    called = {}

    def fake_finder(name):
        called["finder"] = True
        return None

    def fake_factory():
        class F:
            def create(self, name): return SimpleNamespace(name=name, scope=ImportScope.UNKNOWN)
        return F()
    factory = fake_factory()

    def fake_classifier(name, node):
        called["classifier"] = (name, node)
        node.scope = ImportScope.LOCAL
        return node

    resolver = BaseResolver(finder=fake_finder, factory=factory, import_classifier=fake_classifier)
    node = resolver.resolve("MyNode")
    assert node.name == "MyNode"
    assert node.scope == ImportScope.LOCAL
    assert "finder" in called and "classifier" in called


def test_base_resolver_fix_type_and_create():
    resolver = BaseResolver(lambda n: None, SimpleNamespace(create=lambda name: {"name": name}))
    resolver.type_adapter = lambda e: {"wrapped": e}
    resolver.node = {"n": 1}
    resolver._fix_type()
    assert "wrapped" in resolver.node
    assert resolver._create("X") == {"name": "X"}


def test_classifier_import_without_classifier():
    resolver = BaseResolver(None, None)
    resolver.node = SimpleNamespace(name="n")
    # Не должен упасть без import_classifier
    resolver._classifier_import()


# ───────────────────────────────
# FactoryCodeSpan
# ───────────────────────────────
def test_factory_code_span_create_codespan():
    code = "x = 1\n"
    node = ast.parse(code).body[0]
    factory = FactoryCodeSpan(code)
    span = factory.create_codespan(node)
    assert isinstance(span, CodeSpan)
    assert span.start_line == 1
    assert "x =" in span.source


def test_factory_code_span_from_file():
    text = "a = 1\nb = 2\n"
    factory = FactoryCodeSpan("")
    span = factory.create_codespan_from_file(text)
    assert isinstance(span, CodeSpan)
    assert span.start_line == 1
    assert span.end_line >= 2
    assert span.source is None  # ← корректно для этой реализации




# ───────────────────────────────
# AttributeFactory
# ───────────────────────────────
def test_attribute_factory_raises_typeerror_if_called_directly():
    import ast
    factory = AttributeFactory()
    node = ast.parse("x = 1").body[0]
    with pytest.raises(TypeError):
        factory.create(node)


# ───────────────────────────────
# AnalyzerBase
# ───────────────────────────────
def test_analyzer_base_analyze_invokes_visit(monkeypatch):
    g = SimpleNamespace()
    base = AnalyzerBase(g)
    called = {}

    class DummyNode(ast.AST): pass
    node = DummyNode()
    tree = ast.Module(body=[node], type_ignores=[])

    def fake_visit(n):
        called["ok"] = True
    base.visit = fake_visit

    factory = SimpleNamespace(create_codespan=lambda n: None)
    base.analyze(tree, module="mod", factory_codespan=factory)
    assert "ok" in called
    assert base.module == "mod"


# ───────────────────────────────
# Scope
# ───────────────────────────────
def test_scope_lookup_in_parent_chain():
    parent = Scope("parent")
    child = Scope("child", parent=parent)
    parent.symbols["foo"] = 42
    assert child.lookup("foo") == 42
    assert child.lookup("missing") is None


# ───────────────────────────────
# SymbolRepository
# ───────────────────────────────
def test_symbol_repository_push_pop_and_register(capsys):
    repo = SymbolRepository()
    s1 = repo.current
    s2 = repo.push_scope("inner")
    assert s2.parent == s1
    repo.register("x", 123)
    assert repo.resolve("x") == 123

    repo.dump()
    out = capsys.readouterr().out
    assert "Scope" in out and "x" in out

    popped = repo.pop_scope()
    assert popped.name == "inner"
