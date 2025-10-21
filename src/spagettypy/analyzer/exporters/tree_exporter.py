from collections import defaultdict
from pathlib import Path
from typing import Any
from ..graph import GraphX


class TreeDirectoryExporter:
    def __init__(self, root: str = "."):
        self.root = root

    def __call__(self, graph: GraphX) -> str:
        tree: dict[str, list[Any]] = defaultdict(list)

        # Формируем дерево связей на основе графа
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

            tree[u_label].append(v_label)

        # Привязываем вершины без родителей к корню

        all_nodes = set(tree.keys()) | {c for children in tree.values() for c in children}
        for node in all_nodes:
            has_parent = any(node in children for children in tree.values())
            if not has_parent and node != self.root:
                tree[self.root].append(node)

        if "." in tree:
            dot_children = tree.pop(".", [])
            for child in dot_children:
                if child not in tree[self.root]:
                    tree[self.root].append(child)

        # Удаляем возможные упоминания '.' из всех списков потомков
        for children in tree.values():
            while "." in children:
                children.remove(".")

        visited = set()
        stats = {"files": 0, "dirs": 0}

        def _walk(prefix: str, prefix_symbols: list[bool] = [], depth: int = 0) -> list[str]:
            """Рекурсивный проход с прорисовкой вертикальных линий"""
            if prefix in visited:
                return []
            visited.add(prefix)

            lines = []
            children = sorted(
                tree.get(prefix, []),
                key=lambda x: (x not in tree, x.lower()),  # директории первыми
            )

            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                branch = "└── " if is_last else "├── "

                # вертикальные линии от родительских уровней
                line_prefix = "".join("│   " if not last else "    " for last in prefix_symbols)
                lines.append(f"{line_prefix}{branch}{child}")

                # рекурсия
                if child in tree:
                    stats["dirs"] += 1
                    lines.extend(_walk(child, prefix_symbols + [is_last], depth + 1))
                else:
                    stats["files"] += 1

            return lines

        # если '.' является единственным дочерним элементом — начинаем с него
        start_node = self.root
        if len(tree.get(self.root, [])) == 1 and tree[self.root][0] == ".":
            start_node = "."

        lines = _walk(start_node)
        summary = f"\n{stats['files']} files, {stats['dirs']} directories"

        return "\n".join(lines) + summary
