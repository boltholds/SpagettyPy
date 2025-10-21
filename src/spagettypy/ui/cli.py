from ..analyzer.parsers.directory_parser import DirectoryParser,FormatFileChecker,GitignoreFileChecker
import typer
from pathlib import Path
from ..analyzer.graph import GraphX
from ..analyzer.exporters.tree_exporter import TreeDirectoryExporter


app = typer.Typer()
path = Path(r"C:\Users\bolthold\Documents\Code\SpagettyPy")
pythonchecker = FormatFileChecker(".py")
giignore = GitignoreFileChecker(path)
dirparse = DirectoryParser(checkers=[pythonchecker,giignore],base_path=path)
tree_exp = TreeDirectoryExporter(path)
graph = GraphX()


__version__ = "0.1.0"


@app.command()
def tree() -> None:
    ngraph = dirparse(graph=graph,context=path)
    print(tree_exp(ngraph))

def main() -> None:
    app()


if __name__ == "__main__":
    main()