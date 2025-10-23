import ast
from ..model import ModuleInfo, ClassInfo, FunctionInfo
from ..graph.interfaces import GraphProto
from typing import List,Optional
from pathlib import Path

class AnalyzerBase(ast.NodeVisitor):
    def __init__(self, graph:GraphProto):
        super().__init__()
        self.graph = graph
        self.module:Optional[ModuleInfo] = None
        self.current_class:Optional[ClassInfo] = None
        self.functions:List[FunctionInfo] = []


    def analyze(self, tree: ast.AST, module: ModuleInfo):
        self.module = module
        self.visit(tree)

