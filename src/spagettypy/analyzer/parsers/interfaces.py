
from typing import Protocol,Optional, Any, Iterable
from ..graph import GraphX
from pathlib import Path
from ..model import FileInfo

class AnalyzerStage(Protocol):
    def __call__(self, G: GraphX, context: Optional[Any] = None) -> GraphX: ...

class FileChecher(Protocol):
    def __call__(self, file: FileInfo) -> bool: ...
    
class FileFinder(Protocol):
    def __call__(self, propertry: str | Iterable[str]) -> Optional[Path]: ...