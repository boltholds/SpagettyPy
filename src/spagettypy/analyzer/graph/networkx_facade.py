from __future__ import annotations
from typing import Generic, TypeVar, Iterator, Optional, Any
import networkx as nx
from ..model import FileInfo, Relation


N = TypeVar("N")  
R = TypeVar("E", bound=Relation)  


class GraphX(Generic[N, R]):
    
    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_node(self, node: N) -> None:
        self._graph.add_node(node)

    def remove_node(self, node: N) -> None:
        self._graph.remove_node(node)

    def has_node(self, node: N) -> bool:
        return self._graph.has_node(node)

    def nodes(self) -> Iterator[N]:
        return iter(self._graph.nodes)

    def add_edge(self, source: N, target: N, data: Optional[R] = None) -> None:
        self._graph.add_edge(source, target, data=data)

    def remove_edge(self, source: N, target: N) -> None:
        self._graph.remove_edge(source, target)

    def has_edge(self, source: N, target: N) -> bool:
        return self._graph.has_edge(source, target)

    def edges(self) -> Iterator[tuple[N, N, Optional[R]]]:
        for u, v, attrs in self._graph.edges(data=True):
            yield (u, v, attrs.get("data"))

    def children(self, node: N) -> Iterator[N]:
        return self._graph.successors(node)

    def parents(self, node: N) -> Iterator[N]:
        return self._graph.predecessors(node)

    def descendants(self, node: N) -> set[N]:
        return nx.descendants(self._graph, node)

    def ancestors(self, node: N) -> set[N]:
        return nx.ancestors(self._graph, node)

    def get_edge_data(self, source: N, target: N) -> Optional[R]:
        data = self._graph.get_edge_data(source, target, default={})
        return data.get("data")


    def subgraph(self, nodes: list[N]) -> GraphX[N, R]:
        sub = GraphX[N, R]()
        sub._graph = self._graph.subgraph(nodes).copy()
        return sub

    def __len__(self) -> int:
        return len(self._graph)

    def __contains__(self, node: Any) -> bool:
        return node in self._graph

    def __repr__(self) -> str:
        return f"TypedGraph({len(self._graph.nodes)} nodes, {len(self._graph.edges)} edges)"
    
    
    # ------ users methods ------
    def show_summary(self) -> None:
        nodes = list(self._graph.nodes())
        edges = list(self._graph.edges())
        print(f"Узлов: {len(nodes)}")
        print(f"Рёбер: {len(edges)}")
        for u, v, in edges:
            if isinstance(v, FileInfo):
                v_label = str(v.path / f"{v.name}{v.format}")
            else:
                v_label = str(getattr(v, "path", getattr(v, "name", str(v))))
            u_label = str(getattr(u, "path", getattr(u, "name", str(u))))
            relations = self.get_edge_data(u,v)
            print(f"{u.__class__.__name__}:{u_label} --({relations or ""})--> {v.__class__.__name__}:{v_label}")


        

