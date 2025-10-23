from .interfaces import GraphProto
from typing import Iterator, TypeVar, Optional, Type ,Sequence
from pathlib import Path


N = TypeVar("N")  

class FindNodeByName:
    def __init__(self, graph: GraphProto):
        self.graph = graph
    
    def __call__(self,prop: str) -> Optional[N]:
        for node in list(self.graph.nodes()):
            if hasattr(node, "name") and getattr(node, "name") == prop:
                return node
        return None
    
    
from pathlib import Path
from typing import Optional, TypeVar

N = TypeVar("N")

class FindNodeByImportLike:
    """
    Ищет узел в графе по пути импорта, даже если путь укорочен:
    'analyzer.parsers.structure_analyzer' → structure_analyzer из src/spagettypy/analyzer/parsers/
    """

    def __init__(self, graph, root: Path):
        self.graph = graph
        self.root = root.resolve()

    # 🔹 вспомогательная функция для получения нормализованного "пути модуля"
    def _import_path_of(self, node) -> Optional[str]:
        node_path = getattr(node, "path", None)
        node_name = getattr(node, "name", None)
        if not node_path or not node_name:
            return None
        try:
            rel = Path(node_path).relative_to(self.root)
        except ValueError:
            return None

        parts = list(rel.parts)
        # добавляем имя файла без расширения
        parts.append(node_name)
        return ".".join(parts)

    # 🔹 поиск по частичному совпадению пути импорта
    def __call__(self, import_like: str) -> Optional[N]:
        import_like = import_like.strip(".")
        segments = import_like.split(".")
        target_name = segments[-1]

        # Сначала — точное совпадение полного пути
        for node in list(self.graph.nodes()):
            ipath = self._import_path_of(node)
            if ipath and (ipath.endswith(import_like) or ipath == import_like):
                return node

        # Затем — по имени (например, structure_analyzer)
        for node in list(self.graph.nodes()):
            if getattr(node, "name", None) == target_name:
                return node

        return None
