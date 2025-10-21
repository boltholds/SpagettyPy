from collections import defaultdict
from pathlib import Path
from typing import Any
from ..graph import GraphX


class TreeDirectoryExporter:
    def __init__(self, root: str = ".", max_depth: int | None = None, show_summary: bool = True, color: bool = False):
        self.root = root
        self.max_depth = max_depth
        self.show_summary = show_summary
        self.color = color

    def __call__(self, graph: GraphX) -> str:
        tree: dict[str, list[Any]] = defaultdict(list)

        # Построение дерева
        for u, v, _ in graph.edges():
            u_path = Path(getattr(u, "path", getattr(u, "name", str(u))))
            v_path = Path(getattr(v, "path", getattr(v, "name", str(v))))

            u_label = u_path.name or str(u_path)
            # имя файла (если FileInfo) или последняя папка
            if hasattr(v, "name") and hasattr(v, "format"):
                v_label = f"{v.name}{v.format}"
            else:
                v_label = v_path.name or str(v_path)

            if u_label == v_label or v_label == ".":
                continue

            tree[u_label].append(v_label)

        # Привязка孤вершин к корню
        all_nodes = set(tree.keys()) | {c for children in tree.values() for c in children}
        for node in all_nodes:
            if all(node not in children for children in tree.values()) and node != self.root:
                tree[self.root].append(node)

        visited = set()
        stats = {"dirs": 0, "files": 0}

        def _colorize(label: str, is_dir: bool) -> str:
            if not self.color:
                return label
            if is_dir:
                return f"\033[1;34m{label}\033[0m"  # синие папки
            if label.endswith(".py"):
                return f"\033[0;32m{label}\033[0m"  # зелёные .py файлы
            return label

        def _walk(prefix: str, prefix_symbols: list[bool] = [], depth: int = 0) -> list[str]:
            """Рекурсивный проход с прорисовкой вертикальных линий"""
            if prefix in visited:
                return []
            if self.max_depth is not None and depth > self.max_depth:
                return []
            visited.add(prefix)

            lines = []
            children = sorted(tree.get(prefix, []))
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                branch = " └── " if is_last else " ├── "

                line_prefix = "".join(" │  " if not last else "    " for last in prefix_symbols)
                is_dir = child in tree
                label = _colorize(child, is_dir)
                lines.append(f"{line_prefix}{branch}{label}")

                if is_dir:
                    stats["dirs"] += 1
                else:
                    stats["files"] += 1

                lines.extend(_walk(child, prefix_symbols + [is_last], depth + 1))
            return lines

        lines = _walk(self.root)
        if self.show_summary:
            lines.append(f"\n{stats['files']} files, {stats['dirs']} directories")

        return "\n".join(lines)
