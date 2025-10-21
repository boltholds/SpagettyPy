from typing import Protocol,Optional, Any, Iterable
from ..graph import GraphX
from pathlib import Path
from ..model import FileInfo


class ExporterProto(Protocol):
    def __call__(self, G: GraphX) -> Any: ...