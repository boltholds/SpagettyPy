import ast
from ..model import ModuleInfo, ClassInfo, FunctionInfo, CodeSpan, BaseData, ImportScope, AttributeInfo
from ..graph.interfaces import GraphProto, FinderNode
from typing import List,Optional, Generic, Type, Callable, Any, Sequence, Dict
from pathlib import Path
import re
from collections import deque
from dataclasses import field

ScopeType = ModuleInfo | ClassInfo | FunctionInfo


class BaseResolver:
    def __init__(
        self, 
        finder: Any, 
        factory: Any, 
        import_classifier: Optional[Callable] = None,
        type_adapter: Callable[[Any], Any] = lambda e: e
    ):
        self.finder = finder
        self.factory = factory
        self.import_classifier = import_classifier
        self.type_adapter = type_adapter
        self.node: Optional[Any] = None
        self.module: Optional[Any] = None

    def _fix_type(self) -> None:
        if self.node:
            self.node = self.type_adapter(self.node)

    def _create(self, name: str):
        return self.factory.create(name=name)

    def _classifier_import(self):
        if self.node and self.import_classifier:
            result = self.import_classifier(self.node.name, self.node)
            if result is not None:
                self.node = result

    def resolve(self, name: str, module: Optional[Any] = None) -> Any:
        self.module = module
        self.node = self.finder(name)

        # если не найдено — создаём
        if not self.node and self.factory:
            self.node = self._create(name)

        # исправляем тип (например FileInfo -> ModuleInfo)
        self._fix_type()

        # классифицируем область
        if self.node and getattr(self.node, "scope", ImportScope.UNKNOWN) == ImportScope.UNKNOWN:
            self._classifier_import()

        return self.node



class FactoryCodeSpan:
    def __init__(self, source):
        self.source = source
    
    def create_codespan(self,node: ast.AST) -> CodeSpan:
        return CodeSpan(
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            start_col=node.col_offset,
            end_col=getattr(node, "end_col_offset", node.col_offset),
            source=ast.get_source_segment(self.source, node),
        )
    
    def create_codespan_from_file(self, file : Sequence[Optional[Sequence[str]]]) -> CodeSpan:
        total_lines = len(re.findall(r"[\n']+?", file))
        end_col = 1
        if total_lines>0:
            end_col = len(file[total_lines-1])
        return CodeSpan(
            start_line=1,
            end_line=total_lines,
            start_col=1,
            end_col=end_col,
            source=None,
        )




class AttributeFactory:
    def create(self,node: ast.AST) -> AttributeInfo:
        return AttributeInfo()


class AnalyzerBase(ast.NodeVisitor):
    def __init__(self, graph:GraphProto):
        super().__init__()
        self.graph = graph
        self.module:Optional[ModuleInfo] = None
        self.current_class:Optional[ClassInfo] = None
        self.functions:List[FunctionInfo] = []
        self._get_codespan = None


    def analyze(self, tree: ast.AST, module: ModuleInfo, factory_codespan: FactoryCodeSpan):
        self.module = module
        self._get_codespan = factory_codespan.create_codespan
        self.visit(tree)




from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from collections import deque

@dataclass
class Scope:
    name: str
    parent: Optional["Scope"] = None
    symbols: Dict[str, Any] = field(default_factory=dict)

    def lookup(self, name: str) -> Optional[Any]:
        """Ищет символ в текущем или родительских областях."""
        scope = self
        while scope:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None


class SymbolRepository:
    """Глобальный репозиторий (реестр) символов и областей видимости."""
    def __init__(self):
        self.global_scope = Scope("<global>")
        self.scope_stack: deque[Scope] = deque([self.global_scope])

    @property
    def current(self) -> Scope:
        return self.scope_stack[-1]

    def push_scope(self, name: str):
        new_scope = Scope(name=name, parent=self.current)
        self.scope_stack.append(new_scope)
        return new_scope

    def pop_scope(self):
        return self.scope_stack.pop()

    def register(self, name: str, obj: Any):
        """Добавляет объект (FunctionInfo, ClassInfo, ModuleInfo и т.д.) в текущий scope."""
        self.current.symbols[name] = obj

    def resolve(self, name: str) -> Optional[Any]:
        """Разрешает имя начиная с текущей области видимости."""
        return self.current.lookup(name)

    def dump(self):
        """Отладочный вывод"""
        for scope in self.scope_stack:
            print(f"[Scope {scope.name}]")
            for k, v in scope.symbols.items():
                print(f"  {k} -> {type(v).__name__}")
