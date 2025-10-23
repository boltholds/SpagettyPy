from __future__ import annotations
from typing import List, Iterable,Optional, Iterator
from pathlib import Path
import ast
import sys
from importlib.util import find_spec

from ..graph import GraphProto, FindNodeByName, FilterNodeByClass, FindNodeByImportLike
from ..model import (
    Relation, 
    ClassInfo, 
    FunctionInfo, 
    ModuleInfo, 
    FileInfo, 
    ImportScope,
    ClassType,
    FunctionType,
    ImportScope
    )
from .base import AnalyzerBase





class ModuleFileFinder:
    """Ищет файл модуля как в системных путях, так и локально внутри проекта."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        # Добавляем корень проекта в sys.path (а не только src/)
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))

    def _find_local_path(self, prop: str) -> Optional[Path]:
        """
        Ищет модуль по имени 'a.b.c' как файл a/b/c.py или a/b/c/__init__.py
        внутри проекта, без предположений о структуре.
        """
        parts = Path(*prop.split("."))
        candidates = [
            self.root / parts.with_suffix(".py"),
            self.root / parts / "__init__.py",
        ]

        # если структура произвольная — ищем глубже (до 3 уровней вложенности)
        for pyfile in self.root.rglob("*.py"):
            if pyfile.stem == parts.name and parts.parts[-1] in pyfile.parts:
                return pyfile.resolve()

        for path in candidates:
            if path.exists():
                return path.resolve()

        return None

    def __call__(self, prop: str) -> Optional[Path]:
        """Пробует найти модуль через importlib или локальный поиск."""
        try:
            spec = find_spec(prop)
        except ModuleNotFoundError:
            spec = None

        if spec and spec.origin and spec.origin not in {"built-in", "frozen"}:
            return Path(spec.origin)

        # иначе ищем вручную
        return self._find_local_path(prop)
        

class ModuleImportScopeClassifer:
    "Определяет тип модуля по его имени и пути до него"
    def __init__(self, root: Path):
        self.root = root
        self.find_path = ModuleFileFinder(root)
        
        
    def __call__(self, prop: str | Iterable[str], node: ModuleInfo) -> ModuleInfo:
        
        
        names = (prop,) if isinstance(prop, str) else tuple(prop)


        if node.file and Path(node.file.path).exists():
            node.scope = ImportScope.LOCAL
            return node

        for name in names:
            file_path = self.find_path(name)
            if not file_path:
                # если модуль не найден через find_spec, считаем, что это stdlib
                node.scope = ImportScope.STDLIB
                continue

            # Проверяем путь относительно проекта
            if self.root in file_path.parents:
                node.scope = ImportScope.LOCAL
            elif "site-packages" in str(file_path):
                node.scope = ImportScope.DEPENDENCY
            elif "lib" in str(file_path).lower() or "python" in str(file_path).lower():
                node.scope = ImportScope.STDLIB
            else:
                node.scope = ImportScope.UNKNOWN
        return node




class ClassTypeClassifier:
    def __call__(self, prop: Iterable[str], node: ClassInfo) -> ClassInfo:
            node.type = ClassType.NORMAL 
            if "ABC" in prop or "ABCMeta" in prop:
                node.type = ClassType.ABSTRACT
            if "Enum" in prop:
                node.type = ClassType.ENUM
            if "dataclass" in [d.id for d in node.decorators if isinstance(d, ast.Name)]:
                node.type = ClassType.DATACLASS
            
            if "Protocol" in prop:
                node.type = ClassType.PROTOCOL
            return node

        
        

class FileToModuleAdapter:
    def __call__(self, file: FileInfo) -> ModuleInfo:
        return ModuleInfo(name=file.name, file=file, scope=ImportScope.UNKNOWN)
    
class InfoFactoryByName:
    def create_module(self, name: str) -> ModuleInfo:
        return ModuleInfo(name=name)        
    
    def create_class(self, name: str, module: ModuleInfo) -> ClassInfo:
        return ClassInfo(name=name, module=module)  

       
class ASTAnalyzerPipeline:
    def __init__(self, analyzers: list[AnalyzerBase], root_path: Path):
        self.analyzers = analyzers
        self.root_path = root_path
        self.module_scope_classifier = ModuleImportScopeClassifer(root_path)

    def __call__(self, graph: GraphProto) -> GraphProto:
        result = graph
        filterbyclass: Iterator[FileInfo] = FilterNodeByClass(filter_by=FileInfo)
        ony_files:List[FileInfo] = [n for n in filterbyclass(graph)]
        to_module = FileToModuleAdapter()
        for file in ony_files:
            
            module = to_module(file)
            module = self.module_scope_classifier(module.name,module)
            graph.add_edge(file,module,data=Relation.CONTAINS)
            
           
            with open(Path(file.path, file.name + file.format), "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            self.run(tree,module)
        return result
        


    def run(self, tree: ast.AST, module:ModuleInfo):
        for analyzer in self.analyzers:
            analyzer.analyze(tree,module)


class StructureAnalyzer(AnalyzerBase):
    def __init__(self, graph, root: Path):
        super().__init__(graph)
        self.import_classifier = ModuleImportScopeClassifer(root)
        self.find_node = FindNodeByName(graph)
        self.find_class = FindNodeByImportLike(graph=graph,root=root)
        self.to_module = FileToModuleAdapter()
        self.factory = InfoFactoryByName()

    def _resolve_module(self, name: str) -> ModuleInfo:
        """Находит или создаёт и классифицирует модуль по имени."""
        node = self.find_class(name)

        # 1️⃣ Не найден → создаём новый
        if node is None:
            node = self.factory.create_module(name)

        # 2️⃣ Если FileInfo → конвертируем в ModuleInfo
        if isinstance(node, FileInfo):
            node = self.to_module(node)

        # 3️⃣ Классифицируем область (если ещё не определена)
        if getattr(node, "scope", ImportScope.UNKNOWN) == ImportScope.UNKNOWN:
            node = self.import_classifier(node.name, node)

        return node
    
    def _resolve_class(self, name: str, module: ModuleInfo) -> ClassInfo:
        node = self.find_node(name)

        if node is None:
            node = self.factory.create_class(name=name, module=module)

        if getattr(node, "scope", ImportScope.UNKNOWN) == ImportScope.UNKNOWN:
            node.scope = module.scope

        return node

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            imported = self._resolve_module(alias.name)
            self.graph.add_node(imported)
            self.graph.add_edge(self.module, imported, data=Relation.IMPORTS)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        base_name = node.module or ""
        base_module = self._resolve_module(base_name)

        for alias in node.names:
            full_name = f"{base_name}.{alias.name}" if base_name else alias.name
            
            # Проверяем, есть ли модуль с таким путём
            found_module = self.find_class(full_name)
            if found_module and isinstance(found_module, (ModuleInfo, FileInfo)):
                imported = self._resolve_module(full_name)
            else:
                imported = self._resolve_class(alias.name, module=base_module)
            self.graph.add_node(imported)
            self.graph.add_edge(self.module, imported, data=Relation.IMPORTS)

            if base_module and base_module is not imported:
                self.graph.add_edge(imported, base_module, data=Relation.FROM)



    def visit_ClassDef(self, node: ast.ClassDef):
        classifier = ClassTypeClassifier()
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        
        
        
        
        self.current_class = ClassInfo(
            name=node.name,
            attributes=[],
            module=self.module,
            scope=self.module.scope,
        )
        self.current_class = classifier(bases, self.current_class)
        self.graph.add_edge(self.module, self.current_class, data=Relation.DEFINES)
        
        for base in bases:
            base_class = self._resolve_class(base,self.module)
            self.graph.add_edge(self.current_class, base_class,  data=Relation.INHERIT)
        
        
        self.generic_visit(node)


class GlobalVisitor(AnalyzerBase):
    def __init__(self, graph:GraphProto):
        super().__init__(graph)
        self.globals_map = {}

    def visit_Global(self, node: ast.Global):
        # node.names = ['x', 'y']
        self.globals_map.setdefault("global_vars", []).extend(node.names)
        self.generic_visit(node)
    
    


class ReferenceAnalyzer(AnalyzerBase):
    def visit_Attribute(self, node: ast.Attribute):
        # obj.attr
        obj = ast.unparse(node.value)
        attr = node.attr
        self.graph.add_edge(obj, attr, data=Relation.ATTRACCES)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # использование имени переменной
        ctx = type(node.ctx).__name__  # Load, Store, Del
        self.graph.add_node(node.id)
        self.graph.add_edge(self.module, node.id, relation=Relation.USES)
        self.generic_visit(node)
    
    