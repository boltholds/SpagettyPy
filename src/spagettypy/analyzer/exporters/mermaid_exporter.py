from typing import Type, Sequence
from io import StringIO
from enum import StrEnum
from ..graph import GraphProto,FilterEdgeByClass

class Direction(StrEnum):
    TOPDOWN = "TD"
    LEFTRIGHT = "LR"
    BOTOMTOP = "BT"
    RIGHTLEFT = "RL"


def render_mermaid_html(mermaid_code: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
      </script>
    </head>
    <body>
      <pre class="mermaid">
        {mermaid_code}
      </pre>
    </body>
    </html>
    """   


class MermaidExporter:
    def __init__(self, direction: Direction = Direction.TOPDOWN, only_classes:Sequence[Type] = None ):
        self.direction = direction
        if only_classes:
            self.filter = FilterEdgeByClass(filter_by=only_classes)
        
    def __call__(self, graph:GraphProto) -> str:
        buf = StringIO()
        buf.write(f"graph {self.direction.value}\n")
        
        EDGE_STYLE = {
            "imports": "-.->",
            "defines": "-->",
            "inherits": "--|>",
            "uses": "-.->",
            "calls": "-.->",
            "has": "==>",
            "composes": "==>",
            "aggregates": "--o",
        }
        for src, dst, data in self.filter(graph):
            src_id = self._id(src)
            dst_id = self._id(dst)
            label = self._label(data)
            
              
            
            style = EDGE_STYLE.get(label, "-->")
            buf.write(f"    {src_id} {style} {dst_id}\n")

        return render_mermaid_html(buf.getvalue())

    @staticmethod
    def _id(obj):
        if hasattr(obj, "name"):
            return obj.name.replace(".", "_")
        return str(obj).replace(".", "_")

    @staticmethod
    def _label(data):
        if isinstance(data, dict):
            return data.get("type", "")
        return str(data)