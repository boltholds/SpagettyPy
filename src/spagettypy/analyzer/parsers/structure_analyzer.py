from __future__ import annotations
from typing import List, Iterable,Optional, Iterator, Any
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
    ImportScope,
    AttributeInfo
    )
from .base import AnalyzerBase, FactoryCodeSpan, BaseResolver, AttributeFactory



ScopeType = ModuleInfo | ClassInfo | FunctionInfo

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
    def __init__(self, graph: GraphProto):
        self.graph =graph
        
    
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
        if isinstance(file, FileInfo):
            return ModuleInfo(name=file.name, file=file, scope=ImportScope.UNKNOWN)
        return file
    
class ModuleInfoFactoryByName:
    def create(self, name: str) -> ModuleInfo:
        return ModuleInfo(name=name)        

class ClassInfoFactoryByName:   
    def create(self, name: str, module: ModuleInfo) -> ClassInfo:
        return ClassInfo(name=name, module=module)  



class ClassResolver(BaseResolver):
    def _classifier_import(self):
        if self.node and self.module:
            self.node.scope = getattr(self.module, "scope", ImportScope.UNKNOWN)


    def _create(self, name: str):
        return self.factory.create(name=name, module=self.module)


class ModuleResolver(BaseResolver):
    pass



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
            
            full_path = Path(self.root_path, file.path, file.name + file.format)
            if not full_path.exists():
                continue
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
            codespan_factory = FactoryCodeSpan(source)
            
            tree = ast.parse(source)
            module = to_module(file)
            module = self.module_scope_classifier(module.name,module)
            module.span = codespan_factory.create_codespan_from_file(source)
            graph.add_edge(file,module,data=Relation.CONTAINS)
            
            self.run(tree,module,codespan_factory)
            
            f.close()
        return result
        


    def run(self, tree: ast.AST, module:ModuleInfo, codespan: FactoryCodeSpan ):
        for analyzer in self.analyzers:
            analyzer.analyze(tree,module,codespan)



   




class ImportAnalyzer(AnalyzerBase):
    def __init__(self, graph, root: Path):
        super().__init__(graph)  
        self.find_class = FindNodeByImportLike(graph=graph,root=root)
        self.module_resolver = ModuleResolver(
            FindNodeByImportLike(graph=graph, root=root),
            ModuleInfoFactoryByName(),
            ModuleImportScopeClassifer(root),
            FileToModuleAdapter(),
        )
        self.class_resolver = ClassResolver(
            FindNodeByName(graph),
            ClassInfoFactoryByName(),
            None,  # классификатор не нужен
        )
        

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            imported = self.module_resolver.resolve(alias.name)
            if not imported.span:
                imported.span = self._get_codespan(node)
            self.graph.add_node(imported)
            self.graph.add_edge(self.module, imported, data=Relation.IMPORTS)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        base_name = node.module or ""
        base_module = self.module_resolver.resolve(base_name)

        for alias in node.names:
            full_name = f"{base_name}.{alias.name}" if base_name else alias.name
            
            # Проверяем, есть ли модуль с таким путём
            imported = self.find_class(full_name)
            if imported and isinstance(imported, FileInfo):
                imported:ModuleInfo = self.module_resolver.resolve(full_name)
            else:
                imported:ClassInfo = self.class_resolver.resolve(alias.name, module=base_module)
            if not imported.scope:
                imported.scope = self._get_codespan(node)
            self.graph.add_node(imported)
            self.graph.add_edge(self.module, imported, data=Relation.IMPORTS)

            if base_module and base_module is not imported:
                self.graph.add_edge(imported, base_module, data=Relation.FROM)




class StructureAnalyzer(AnalyzerBase):
    def __init__(self, graph):
        super().__init__(graph)

        self.class_resolver = ClassResolver(
            FindNodeByName(graph),
            ClassInfoFactoryByName(),
            None,  # классификатор не нужен
        )
        self.attribute_factory = AttributeFactory()


    def visit_ClassDef(self, node: ast.ClassDef):
        classifier = ClassTypeClassifier(self.graph)
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        
        
        self.current_class = ClassInfo(
            name=node.name,
            module=self.module,
            scope=self.module.scope,
            span=self._get_codespan(node)
        )
        self.current_class = classifier(bases, self.current_class)
        self.graph.add_edge(self.module, self.current_class, data=Relation.DEFINES)
        
        for base in bases:
            base_class = self.class_resolver.resolve(base,self.module)
            self.graph.add_edge(self.current_class, base_class,  data=Relation.INHERIT)
        
        
                # --- поля внутри класса ---
        for stmt in node.body:
            # 1️⃣ обычные присваивания
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        
                        attribute = AttributeInfo(
                            name=target.id,value= ast.unparse(stmt.value),
                            annotation="None",
                            level="class", 
                            scope=self.module.scope
                            )
                        self.graph.add_edge(self.current_class, attribute,  data=Relation.ATTRIBUTE)

            # 2️⃣ аннотированные поля
            elif isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Name):
                    annotation = (
                        ast.unparse(stmt.annotation)
                        if stmt.annotation else None
                    )
                    
                    attribute = AttributeInfo(
                        name=stmt.target.id,
                        value=stmt.value,
                        annotation=annotation,
                        level="class",
                        scope=self.module.scope
                        )
                    self.graph.add_edge(self.current_class, attribute,  data=Relation.ATTRIBUTE)

        # --- ищем instance-поля в методах ---
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                for sub in ast.walk(stmt):
                    if (
                        isinstance(sub, ast.Assign)
                        and isinstance(sub.targets[0], ast.Attribute)
                        and isinstance(sub.targets[0].value, ast.Name)
                        and sub.targets[0].value.id == "self"
                    ):
                        attr_name = sub.targets[0].attr
                        
                        attribute = AttributeInfo(
                            name=attr_name,value= ast.unparse(sub.value),
                            annotation="None",
                            level="instance",
                            scope=self.module.scope
                            )
                        self.graph.add_edge(self.current_class, attribute,  data=Relation.ATTRIBUTE)
        
        
        
        self.generic_visit(node)
        
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        
        args_types: List[str] = []
        defaults: List[str] = []
        returns: Optional[str] = None
        # ---- аргументы ----
        for arg in node.args.args:
            annotation = None
            if arg.annotation:
                annotation = ast.unparse(arg.annotation)  # str: 'int', 'str | None'
            args_types.append(annotation or "Any")

        # ---- значения по умолчанию ----
        for d in node.args.defaults:
            defaults.append(ast.unparse(d))


        # ---- возвращаемое значение ----
        if node.returns:
            returns = ast.unparse(node.returns)
        else:
            returns = "None"
        
        fi = FunctionInfo(
            name=node.name,
            module=self.module,
            type = FunctionType.CORUTINE if isinstance(node, ast.AsyncFunctionDef) else FunctionType.SYNC,
            scope=self.module.scope,
            span=self._get_codespan(node),
            return_type=returns,
            args_types=args_types
            )
        self.graph.add_node(fi)
        if self.current_class:
            self.graph.add_edge(self.current_class, fi, data=Relation.METHODS)
        else:
            self.graph.add_edge(self.module, fi, data=Relation.METHODS)
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
        self.graph.add_edge(self.module, node.id, data=Relation.USES)
        self.generic_visit(node)
    



class CallAnalyzer(AnalyzerBase):
    """Анализ вызовов функций и методов (Call)."""

    def visit_Call(self, node: ast.Call):
        


        self.generic_visit(node)
        
        
        
    def classify_call(self, node: ast.Call) -> dict:
        func_src = ast.unparse(node.func)
        args = [ast.unparse(a) for a in node.args]
        kwargs = {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg}

        # определяем тип выражения
        if isinstance(node.func, ast.Name):
            call_type = "function"
            caller = None
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_type = "method"
            caller = ast.unparse(node.func.value)
            name = node.func.attr
        elif isinstance(node.func, ast.Call):
            call_type = "dynamic"
            caller = None
            name = ast.unparse(node.func)
        else:
            call_type = "unknown"
            caller = None
            name = ast.unparse(node.func)

        return {
            "lineno": node.lineno,
            "call_type": call_type,
            "caller": caller,
            "callee": name,
            "args": args,
            "kwargs": kwargs,
            "expr": func_src,
        }