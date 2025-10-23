import typer
from pathlib import Path
from ...analyzer.exporters.tree_exporter import DirectoryFormatter, TreeExporter,ShowSummary
from ...analyzer.exporters.mermaid_exporter import MermaidExporter
from ...analyzer.parsers.structure_analyzer import ASTAnalyzerPipeline,StructureAnalyzer, GlobalVisitor
from ...analyzer.model import ClassInfo, ModuleInfo,FunctionInfo

app = typer.Typer(help="Генерация UML")

@app.command()
def analyze(ctx: typer.Context)-> None:
    """Построить диаграмму"""
    cfg = ctx.obj
    base_path = cfg["root"]
    graph = cfg["graph"]
    ast = ASTAnalyzerPipeline(analyzers=[StructureAnalyzer(graph,base_path),GlobalVisitor(graph)],root_path=base_path)
    agraph = ast(graph)
    to_mermaid = MermaidExporter(only_classes=(ModuleInfo, FunctionInfo, ClassInfo))
    
    path = Path(base_path,"diagram.html")

    
    summaryzate = ShowSummary()
    
    typer.echo(summaryzate(agraph))

export_app = typer.Typer(help="Экспорт UML-диаграмм в разные форматы")

@export_app.command("to")
def export_to(format: str = typer.Argument(..., help="Формат: mermaid / plantuml / dot / json")):
    """Экспортировать диаграмму в указанный формат"""
    typer.echo(f"Экспортируем UML в формат: {format}")


@app.command()
def tree(ctx: typer.Context) -> None:
    """Показать дерево проекта или текущей дирректории"""
    cfg = ctx.obj
    base_path = cfg["root"]
    graph = cfg["graph"]
    tree_exp = TreeExporter(formatter=DirectoryFormatter(), root=base_path)
    typer.echo(tree_exp(graph))

# подключаем подприложение
app.add_typer(export_app, name="export")



     
        
