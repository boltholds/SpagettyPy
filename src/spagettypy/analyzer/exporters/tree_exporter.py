from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Set, Optional
from dataclasses import fields
from ..graph import GraphProto,FilterNodeByClass
from .interfaces import TreeFormatter
from ..model import FileInfo,DirectoryNode

from tabulate import tabulate

class TreeExporter:
    def __init__(self,formatter:TreeFormatter,  root: str = "."):
        self.root = root
        self.tree: dict[str, list[Any]]  = defaultdict(list)
        self.visited:Set[str] = set()
        self.stats = {"files": 0, "dirs": 0}
        
    def _collect_tree(self,graph: GraphProto):
        """Формируем дерево связей на основе графа"""

        
        for u, v,_ in graph.edges():
            u_path = Path(getattr(u, "path", getattr(u, "name", str(u))))
            v_path = Path(getattr(v, "path", getattr(v, "name", str(v))))

            u_label = u_path.name or str(u_path)
            if hasattr(v, "name") and hasattr(v, "format"):
                v_label = f"{v.name}{v.format}"
            else:
                v_label = v_path.name or str(v_path)

            if u_label == v_label or v_label == ".":
                continue

            self.tree[u_label].append(v_label)
            
    def _align_to_root(self):
        # Привязываем вершины без родителей к корню
        all_nodes = set(self.tree.keys()) | {c for children in self.tree.values() for c in children}
        for node in all_nodes:
            has_parent = any(node in children for children in self.tree.values())
            if not has_parent and node != self.root:
                self.tree[self.root].append(node)

        if "." in self.tree:
            dot_children = self.tree.pop(".", [])
            for child in dot_children:
                if child not in self.tree[self.root]:
                    self.tree[self.root].append(child)


    def _remove_root_dir(self):
        # Удаляем возможные упоминания '.' из всех списков потомков
        for children in self.tree.values():
            while "." in children:
                children.remove(".")


    def _walk(self,prefix: str, prefix_symbols: list[bool] = [], depth: int = 0) -> list[str]:
        """Рекурсивный проход с прорисовкой вертикальных линий"""
        if prefix in self.visited:
            return []
        self.visited.add(prefix)

        lines = []
        children = sorted(
            self.tree.get(prefix, []),
            key=lambda x: (x not in self.tree, x.lower()),  # директории первыми
        )

        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            branch = "└── " if is_last else "├── "

            # вертикальные линии от родительских уровней
            line_prefix = "".join("│   " if not last else "    " for last in prefix_symbols)
            lines.append(f"{line_prefix}{branch}{child}")

            # рекурсия
            if child in self.tree:
                self.stats["dirs"] += 1
                lines.extend(self._walk(child, prefix_symbols + [is_last], depth + 1))
            else:
                self.stats["files"] += 1

        return lines

    def __call__(self, graph: GraphProto) -> str:

        self._collect_tree(graph)
        self._align_to_root()
        self._remove_root_dir()

        # если '.' является единственным дочерним элементом — начинаем с него
        start_node = self.root
        if len(self.tree.get(self.root, [])) == 1 and self.tree[self.root][0] == ".":
            start_node = "."

        lines = self._walk(start_node)
        summary = f"\n{self.stats['files']} files, {self.stats['dirs']} directories"

        return "\n".join(lines) + summary

class DirectoryFormatter:
    def get_label(self, node):
        path = Path(getattr(node, "path", getattr(node, "name", str(node))))
        return path.name or str(path)

    def get_children(self, node, graph):
        return [v for u, v, _ in graph.edges() if u == node]
    
    def get_stats(self, graph: Any) -> Dict[str,int]:
        filter_by_dirnfile = FilterNodeByClass(filter_by=(DirectoryNode, FileInfo))

        
        stats = { "files" :0,"dicrectories":0}
        
         

class ClassFormatter:
    def get_label(self, node):
        return getattr(node, "qualname", getattr(node, "name", str(node)))

    def get_children(self, node, graph):
        # дети — это классы, у которых этот класс в списке bases
        return [v for u, v, _ in graph.edges() if u == node]



class ShowSummary:
    def __init__(self):
        self.headers = ["Field", "Value"]
    
    
    def _dataclass_table(self,node:Any) -> str:
        """Возвращает таблицу dataclass как многострочную строку."""
        
        rows = []
        for f in fields(node):
            value = getattr(node, f.name)
            rows.append((f.name, value))
        return tabulate(rows, headers=self.headers, tablefmt="grid").splitlines()
            
    def draw_relations(self, left_node: Any, right_node: Any, label_relation:Optional[str] = None, gap:int = 6) -> str:
        
        result = []
        left_table =self._dataclass_table(left_node)
        right_table = self._dataclass_table(right_node)
        
        max_left_width = max(len(line) for line in left_table)
        total_lines = max(len(left_table), len(right_table))
        left_table += [" " * max_left_width] * (total_lines - len(left_table))
        right_table += [""] * (total_lines - len(right_table))
        
        arrow = f" --------> "
        if label_relation:
            arrow = f" --({label_relation})--> "
        else:
            label_relation = ""
        
        result.append(f"{left_node.__class__.__name__:<{max_left_width}}{' ' * gap}{' ' * len(arrow)}{right_node.__class__.__name__}\n")
        for la, lb in zip(left_table, right_table):
            result.append(f"{la:<{max_left_width}}{' ' * gap}{arrow if 'Field' in la else ' ' * len(arrow)}{lb}\n")
        middle = total_lines // 2
        result.append(" " * (max_left_width + gap) + f"{label_relation:^5}\n")

        
        return "".join(result)
        
    
    def __call__(self, graph: GraphProto) -> str:
        result = []

        for u, v,data in graph.edges():

            line = self.draw_relations(left_node=u,right_node=v,label_relation=data)
            result.append(line)
            result.append("\n")

            
            
        return "".join(result)