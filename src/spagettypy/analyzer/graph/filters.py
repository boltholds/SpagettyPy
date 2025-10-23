from .interfaces import GraphProto
from typing import Iterator, TypeVar, Optional,Type, Sequence,Generic
import inspect
from ..model import Relation


N = TypeVar("N") 
Rel = TypeVar("Rel", bound=Relation)
T = TypeVar("T")


class BaseTypeFilter(Generic[T]):
    def __init__(self, filter_by: Type[T] | Sequence[Type[T]], include: bool = True):
        self.include = include

        if isinstance(filter_by, Sequence) and not isinstance(filter_by, (str, bytes, bytearray)):
            self.filter_by: tuple[Type[T], ...] = tuple(filter_by)
        else:
            self.filter_by = (filter_by,)

    def match(self, obj: object) -> bool:
        return isinstance(obj, self.filter_by)
            



class FilterNodeByClass(BaseTypeFilter):
    def __call__(self, graph: GraphProto) -> Iterator[N]:
        if self.filter_by:
            edges = list(graph.edges())
            for u, v, data in edges:
                if self.include == isinstance(v, self.filter_by) :
                    yield v
                if self.include == isinstance(u, self.filter_by):
                    yield u


class FilterEdgeByClass(BaseTypeFilter):
    
    def __call__(self, graph: GraphProto) -> Iterator[tuple[N,N,Optional[str]]]:
        if self.filter_by:
            edges = list(graph.edges())
            for u, v, data in edges:
                if self.include == (isinstance(v, self.filter_by) and isinstance(u, self.filter_by)):
                    yield u, v, data
                    

class FilterEdgeByRelations(BaseTypeFilter[Rel]):
    def __call__(self, graph: GraphProto) -> Iterator[tuple[N,N,Optional[str]]]:
        if self.filter_by:
            edges = list(graph.edges())
            for u, v, data in edges:
                if self.include == (data in self.filter_by):
                    yield u, v, data