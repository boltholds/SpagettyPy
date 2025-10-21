from ..analyzer.parsers.directory_parser import DirectoryParser,FormatFileChecker,GitignoreFileChecker
import typer
from pathlib import Path
from ..analyzer.graph import GraphX
from ..analyzer.exporters.tree_exporter import TreeDirectoryExporter

__version__ = "0.1.0"
app = typer.Typer(help=f"SpagettyPy — Python AST → UML visualizer {__version__}v")



@app.command()
def uml()-> None:
    """Построить диаграмму"""

@app.command()
def tree(
    path: Path = typer.Option(".", help="Путь к проекту")
) -> None:
    """Показать дерево проекта или текущей дирректории"""
    base_path = path.resolve()
    pythonchecker = FormatFileChecker(".py")
    gitignore = GitignoreFileChecker(base_path)
    dirparse = DirectoryParser(checkers=[pythonchecker, gitignore], base_path=base_path)
    tree_exp = TreeDirectoryExporter(base_path)
    graph = GraphX()

    ngraph = dirparse(graph=graph, context=base_path)
    typer.echo(tree_exp(ngraph))



