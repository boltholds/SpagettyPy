from ..analyzer.parsers.directory_parser import DirectoryParser,FormatFileChecker,GitignoreFileChecker,ExcludeFileChecher
import typer
from pathlib import Path
from ..analyzer.graph import GraphX
from .commands import have


app = typer.Typer(help=f"SpagettyPy — Python AST → UML visualizer")
app.add_typer(have.app, name="have", help="Работа с UML")
app.add_typer(have.app, name="get")

@app.callback()
def main(
    ctx: typer.Context,
    exclude: list[str] = typer.Option([], "--exclude", "-e"),
    gitignore: bool = typer.Option(False, "--gitignore"),
    only_python: bool = typer.Option(False, "--only_python"),
    path: Path = typer.Option(".","--path", help="Путь к проекту")
):  
    base_path = path.resolve()
    checkers = []
    if gitignore:
        checkers.append(GitignoreFileChecker(base_path))
    if exclude:
        checkers.append(ExcludeFileChecher(excludes=exclude))
    if only_python:
        checkers.append(FormatFileChecker(".py"))
    graph = GraphX()
    dirparse = DirectoryParser(checkers=checkers, base_path=base_path)
    ngraph = dirparse(graph=graph, context=base_path)
    ctx.obj = {"root" : base_path, "graph": ngraph}






