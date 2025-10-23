
from typing import Protocol,Optional, Any, Iterable, TypeVar, Type
from pathlib import Path
from ..model import FileInfo,ClassInfo, ModuleInfo, FunctionInfo
from ..graph import GraphProto

AstNodeType = ClassInfo | ModuleInfo | FunctionInfo
T = TypeVar("T", bound=AstNodeType)

class AnalyzerStageProto(Protocol):
    def __call__(self, graph: GraphProto, context: Optional[Any] = None) -> GraphProto: ...

class FileChecherProto(Protocol):
    def __call__(self, file: FileInfo) -> bool: ...
    
class FileFinderProto(Protocol):
    def __call__(self, prop: str) -> Optional[Path]: ...
    
class ASTNodeClassifierProto(Protocol[T]):
    def __call__(self, prop: str | Iterable[str], node: T) -> T: ...

