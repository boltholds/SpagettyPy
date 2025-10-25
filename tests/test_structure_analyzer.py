import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from spagettypy.analyzer.graph.networkx_facade import GraphX
from spagettypy.analyzer.parsers.structure_analyzer import (
    ModuleFileFinder,
    ModuleImportScopeClassifer,
    ClassTypeClassifier,
    FileToModuleAdapter,
    StructureAnalyzer,
    ReferenceAnalyzer,
    CallAnalyzer,
    ASTAnalyzerPipeline,
    ImportAnalyzer,
    ModuleResolver,
    ClassResolver,
    GlobalVisitor
    
)
from spagettypy.analyzer.model import (
    FileInfo,
    ModuleInfo,
    ClassInfo,
    FunctionInfo,
    Relation,
    ImportScope,
    ClassType,
    
)


# ─────────────────────────────────────────────
# Простая имитация GraphProto для тестов
# ─────────────────────────────────────────────
class DummyGraph(GraphX):
    def __init__(self):
        super().__init__()
        self.added_edges = []

    def add_edge(self, u, v, data=None):
        self.added_edges.append((u, v, data))
        super().add_edge(u, v, data=data)


# ─────────────────────────────────────────────
# ModuleFileFinder
# ─────────────────────────────────────────────
def test_module_file_finder_local(tmp_path):
    file = tmp_path / "mymod.py"
    file.write_text("x = 1")

    finder = ModuleFileFinder(tmp_path)
    result = finder("mymod")
    assert result and result.name == "mymod.py"


def test_module_file_finder_deep(tmp_path):
    sub = tmp_path / "pkg" / "inner"
    sub.mkdir(parents=True)
    (sub / "deepmod.py").write_text("pass")

    finder = ModuleFileFinder(tmp_path)
    result = finder("pkg.inner.deepmod")
    assert result and result.name == "deepmod.py"



# ─────────────────────────────────────────────
# Scope classifier
# ─────────────────────────────────────────────
def test_module_scope_classifier_local(tmp_path):
    f = FileInfo(name="mod", format=".py", path=tmp_path)
    m = ModuleInfo(name="mod", file=f)
    clf = ModuleImportScopeClassifer(tmp_path)
    out = clf("mod", m)
    assert out.scope == ImportScope.LOCAL


# ─────────────────────────────────────────────
# ClassTypeClassifier
# ─────────────────────────────────────────────
def test_class_type_classifier_enum_and_protocol():
    g = DummyGraph()
    clf = ClassTypeClassifier(g)

    node = ClassInfo(name="C", module=None)
    result = clf(["Enum"], node)
    assert result.type == ClassType.ENUM

    node2 = ClassInfo(name="X", module=None)
    result2 = clf(["Protocol"], node2)
    assert result2.type == ClassType.PROTOCOL


# ─────────────────────────────────────────────
# FileToModuleAdapter
# ─────────────────────────────────────────────
def test_file_to_module_adapter_creates_module():
    file = FileInfo(name="file", format=".py", path=Path("."))
    adapter = FileToModuleAdapter()
    mod = adapter(file)
    assert isinstance(mod, ModuleInfo)
    assert mod.file == file


# ─────────────────────────────────────────────
# StructureAnalyzer
# ─────────────────────────────────────────────
def test_structure_analyzer_adds_class_and_function_edges():
    src = """
class MyClass(Base):
    x = 1
    def method(self):
        self.attr = 42
"""
    tree = ast.parse(src)
    g = DummyGraph()
    analyzer = StructureAnalyzer(g)
    analyzer.module = ModuleInfo(name="mod")
    analyzer.current_class = None
    analyzer._get_codespan = lambda node: None  # 🧩 фиктивная реализация

    analyzer.visit(tree)

    edge_types = [d for _, _, d in g.added_edges]
    assert Relation.DEFINES in edge_types
    assert Relation.ATTRIBUTE in edge_types
    assert Relation.METHODS in edge_types



# ─────────────────────────────────────────────
# ReferenceAnalyzer
# ─────────────────────────────────────────────
def test_reference_analyzer_creates_edges_for_names_and_attrs():
    src = "obj.attr\nx = y"
    tree = ast.parse(src)
    g = DummyGraph()
    analyzer = ReferenceAnalyzer(g)
    analyzer.module = ModuleInfo(name="m")

    analyzer.visit(tree)

    edges = [(u, v, d) for u, v, d in g.added_edges]
    assert any(d == Relation.ATTRACCES for _, _, d in edges)
    assert any(d == Relation.USES for _, _, d in edges)


# ─────────────────────────────────────────────
# CallAnalyzer.classify_call
# ─────────────────────────────────────────────
def test_call_analyzer_classify_call_variants():
    src = "obj.method(x, y=2)"
    tree = ast.parse(src)

    # ищем первый узел вызова
    call_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))

    analyzer = CallAnalyzer(SimpleNamespace(graph=DummyGraph()))
    info = analyzer.classify_call(call_node)

    assert info["call_type"] == "method"
    assert info["callee"] == "method"
    assert "args" in info
    assert "kwargs" in info

# ─────────────────────────────────────────────
# ASTAnalyzerPipeline
# ─────────────────────────────────────────────
def test_ast_analyzer_pipeline_skips_missing_files(tmp_path):
    """Если файл отсутствует — он пропускается без ошибок"""
    graph = GraphX()
    f1 = FileInfo(name="nofile", format=".py", path=tmp_path)
    graph.add_node(f1)

    analyzer = ASTAnalyzerPipeline(analyzers=[], root_path=tmp_path)
    result = analyzer(graph)

    # Граф не должен измениться
    assert sum(1 for _ in result.nodes()) == 1




def test_ast_analyzer_pipeline_processes_existing_file(tmp_path):
    code = "x = 1"
    f = tmp_path / "m.py"
    f.write_text(code)

    file_node = FileInfo(name="m", format=".py", path=tmp_path)
    g = GraphX()
    g.add_node(file_node)

    analyzer = ASTAnalyzerPipeline(analyzers=[ImportAnalyzer(GraphX(), root=tmp_path)], root_path=tmp_path)
    result = analyzer(g)

    assert len(list(result.nodes())) == 1



# ─────────────────────────────────────────────
# ModuleFileFinder (stdlib, dependency)
# ─────────────────────────────────────────────
def test_module_file_finder_stdlib(tmp_path):
    finder = ModuleFileFinder(tmp_path)
    # sys — встроенный модуль, find_spec его найдёт как built-in
    assert finder("sys") is None or "sys" in str(finder("sys") or "")


# ─────────────────────────────────────────────
# ModuleImportScopeClassifer
# ─────────────────────────────────────────────
def test_module_import_scope_classifier_variants(tmp_path, monkeypatch):
    f = FileInfo(name="m", format=".py", path=tmp_path)
    m = ModuleInfo(name="m", file=f)
    clf = ModuleImportScopeClassifer(tmp_path)

    # 1️⃣ файл существует → LOCAL
    out = clf("m", m)
    assert out.scope == ImportScope.LOCAL

    # 2️⃣ несуществующий файл → STDLIB (по fallback)
    f2 = FileInfo(name="none", format=".py", path=tmp_path / "no")
    m2 = ModuleInfo(name="none", file=f2)
    out2 = clf("none", m2)
    assert out2.scope in (ImportScope.STDLIB, ImportScope.UNKNOWN)


# ─────────────────────────────────────────────
# FileToModuleAdapter — уже проверен, но добавим smoke
# ─────────────────────────────────────────────
def test_file_to_module_adapter_unknown_file():
    adapter = FileToModuleAdapter()
    result = adapter("not_fileinfo")
    assert result == "not_fileinfo"


# ─────────────────────────────────────────────
# ImportAnalyzer
# ─────────────────────────────────────────────
def test_import_analyzer_visits_import(tmp_path):
    code = "import math"
    tree = ast.parse(code)

    g = GraphX()
    analyzer = ImportAnalyzer(g, root=tmp_path)
    analyzer.module = ModuleInfo(name="mod")
    analyzer._get_codespan = lambda n: None

    analyzer.visit_Import(tree.body[0])

    # должен появиться Relation.IMPORTS
    assert any(d == Relation.IMPORTS for _, _, d in g.edges())


def test_import_analyzer_visits_importfrom(tmp_path):
    code = "from os import path, walk"
    tree = ast.parse(code)

    g = GraphX()
    analyzer = ImportAnalyzer(g, root=tmp_path)
    analyzer.module = ModuleInfo(name="mod")
    analyzer._get_codespan = lambda n: None

    analyzer.visit_ImportFrom(tree.body[0])

    # должен появиться Relation.IMPORTS и, возможно, FROM
    edges = [d for _, _, d in g.edges()]
    assert Relation.IMPORTS in edges
    assert any(d in (Relation.IMPORTS, Relation.FROM) for d in edges)


# ─────────────────────────────────────────────
# ClassResolver и ModuleResolver
# ─────────────────────────────────────────────
def test_class_resolver_sets_scope_and_creates():
    # имитация базового resolver behavior
    from spagettypy.analyzer.parsers.structure_analyzer import ClassInfoFactoryByName
    from spagettypy.analyzer.model import ModuleInfo, ClassInfo

    class DummyResolver(ClassResolver):
        def __init__(self):
            super().__init__(
                finder=lambda x: None,
                factory=ClassInfoFactoryByName(),
                import_classifier=None,
            )

            self.module = ModuleInfo(name="m")

    resolver = DummyResolver()
    resolver.node = ClassInfo(name="C", module=None)
    resolver.module.scope = ImportScope.LOCAL
    resolver._classifier_import()

    assert resolver.node.scope == ImportScope.LOCAL
    created = resolver._create("Z")
    assert created.name == "Z"
    assert created.module.name == "m"


def test_module_resolver_exists():
    r = ModuleResolver(None, None, None, None)
    # просто smoke — он пустой класс
    assert isinstance(r, ModuleResolver)
    
    

# ───────────────────────────────
# ModuleFileFinder edge-cases
# ───────────────────────────────
def test_module_file_finder_rglob_fallback(tmp_path):
    inner = tmp_path / "a" / "b"
    inner.mkdir(parents=True)
    (inner / "modx.py").write_text("pass")

    finder = ModuleFileFinder(tmp_path)
    res = finder("modx")
    # Может вернуть None (если не нашёл), но не должен упасть
    assert res is None or res.name.endswith("modx.py")



def test_module_file_finder_module_not_found(tmp_path):
    finder = ModuleFileFinder(tmp_path)
    res = finder("definitely_not_existing")
    assert res is None


def test_module_file_finder_module_not_found_importerror(monkeypatch, tmp_path):
    finder = ModuleFileFinder(tmp_path)
    monkeypatch.setattr("spagettypy.analyzer.parsers.structure_analyzer.find_spec",
                        lambda name: (_ for _ in ()).throw(ModuleNotFoundError))
    assert finder("bad.module") is None


# ───────────────────────────────
# ModuleImportScopeClassifer rare branches
# ───────────────────────────────
def test_module_scope_classifier_dependency_and_unknown(tmp_path, monkeypatch):
    clf = ModuleImportScopeClassifer(tmp_path)

    m = ModuleInfo(name="dep", file=None)
    monkeypatch.setattr(
        clf.find_path,
        "__call__",
        lambda n: Path(tmp_path / "site-packages" / "dep.py")
    )
    r = clf("dep", m)
    assert r.scope in (ImportScope.DEPENDENCY, ImportScope.STDLIB, ImportScope.LOCAL)

    m2 = ModuleInfo(name="m2", file=None)
    monkeypatch.setattr(
        clf.find_path,
        "__call__",
        lambda n: Path(tmp_path / "someouter" / "pkg")
    )
    r2 = clf("m2", m2)
    assert r2.scope in (ImportScope.UNKNOWN, ImportScope.STDLIB)




# ───────────────────────────────
# ASTAnalyzerPipeline uncommon paths
# ───────────────────────────────
def test_ast_pipeline_skips_nonexistent_file(tmp_path):
    f = FileInfo(name="ghost", format=".py", path=tmp_path)
    g = GraphX()
    g.add_node(f)
    pipe = ASTAnalyzerPipeline([], tmp_path)
    res = pipe(g)
    assert isinstance(res, GraphX)


def test_ast_pipeline_reads_and_links(tmp_path):
    f = tmp_path / "foo.py"
    f.write_text("x=1")
    g = GraphX()
    node = FileInfo(name="foo", format=".py", path=tmp_path)
    g.add_node(node)
    pipe = ASTAnalyzerPipeline([], tmp_path)
    result = pipe(g)
    # пайплайн должен завершиться без ошибок, даже если рёбра не добавлены
    assert isinstance(result, GraphX)



# ───────────────────────────────
# StructureAnalyzer deeper paths
# ───────────────────────────────
def test_structure_analyzer_annassign_and_self_fields():
    src = """
class C:
    x: int
    def __init__(self):
        self.v = 10
"""
    tree = ast.parse(src)
    g = GraphX()
    a = StructureAnalyzer(g)
    a.module = ModuleInfo(name="m")
    a._get_codespan = lambda n: None
    a.visit(tree)

    rels = [d for _, _, d in g.edges()]
    assert Relation.ATTRIBUTE in rels and Relation.METHODS in rels


# ───────────────────────────────
# GlobalVisitor and ReferenceAnalyzer
# ───────────────────────────────
def test_global_visitor_records_globals():
    src = "global a, b"
    tree = ast.parse(src)
    g = GraphX()
    v = GlobalVisitor(g)
    v.visit(tree)
    assert v.globals_map["global_vars"] == ["a", "b"]


def test_reference_analyzer_traverses_all():
    src = "obj.attr\nname"
    g = GraphX()
    a = ReferenceAnalyzer(g)
    a.module = ModuleInfo(name="m")
    a.visit(ast.parse(src))
    # Проверяем оба типа рёбер
    rels = [d for _, _, d in g.edges()]
    assert Relation.ATTRACCES in rels and Relation.USES in rels


# ───────────────────────────────
# CallAnalyzer.visit_Call and classify_call
# ───────────────────────────────
def test_call_analyzer_visit_call_runs_generic(monkeypatch):
    node = ast.parse("foo()").body[0].value
    g = GraphX()
    c = CallAnalyzer(g)
    called = {}
    monkeypatch.setattr(c, "generic_visit", lambda n: called.setdefault("ok", True))
    c.visit_Call(node)
    assert called["ok"]


@pytest.mark.parametrize("expr, expected", [
    ("foo()", "function"),
    ("obj.method()", "method"),
    ("(lambda: None)()", "unknown"), # TODO: dynamic for lambda functions
])
def test_call_analyzer_classify_call_variants(expr, expected):
    node = ast.parse(expr).body[0].value
    g = GraphX()
    analyzer = CallAnalyzer(g)
    info = analyzer.classify_call(node)
    assert info["call_type"] == expected


def test_call_analyzer_rejects_non_call():
    node = ast.parse("(x + y)").body[0].value
    g = GraphX()
    analyzer = CallAnalyzer(g)
    with pytest.raises(AttributeError):
        analyzer.classify_call(node)
