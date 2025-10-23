from typing import Protocol,Any, List, Dict
from ..graph import GraphProto


class ExporterProto(Protocol):
    def __call__(self, G: GraphProto) -> Any: ...



class TreeFormatter(Protocol):
    """Определяет, как из узлов графа получить метки и связи."""
    def get_label(self, node: Any) -> str: ...
    def get_children(self, node: Any, graph: Any) -> List[Any]: ...
    def get_stats(self, graph: Any) -> Dict[str,int]:...
