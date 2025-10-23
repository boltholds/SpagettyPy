from typing import Protocol, TypeVar, Optional,Iterator, Any
from ..model import Relation

N = TypeVar("N")  
E = TypeVar("E", bound=Relation)  


class GraphProto(Protocol[N,E]):
    def add_edge(self, source: N, target: N, data: Optional[E] = None) -> None:...
    def add_node(self, node: N) -> None:...
    def edges(self) -> Iterator[tuple[N, N, Optional[E]]]:...
    def nodes(self) -> Iterator[N]:...
    
class FilerNode(Protocol):
    def __call__(self, graph: GraphProto) -> Iterator[N]:...


class FilerEdge(Protocol):
    def __call__(self, graph: GraphProto) -> Iterator[N]:...
    
    
class FinderNode(Protocol):
    def __call__(self, prop: Any, graph: GraphProto) -> Optional[N]:...


class FinderEdge(Protocol):
    def __call__(self, prop: Any, graph: GraphProto) -> tuple[N, N, Optional[E]]:...