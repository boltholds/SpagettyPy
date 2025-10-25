import pytest
from typer.testing import CliRunner
from pathlib import Path
from spagettypy.ui.cli import app

runner = CliRunner()


def test_cli_help():
    """CLI должен запускаться и показывать help без ошибок"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "SpagettyPy" in result.stdout
    assert "have" in result.stdout or "get" in result.stdout


def test_cli_with_options(tmp_path):
    """Smoke-тест CLI с опциями, проверяет создание контекста"""
    # создаём временную структуру проекта
    (tmp_path / "a.py").write_text("print('ok')")

    result = runner.invoke(
        app,
        [
            "--only_python",
            "--path",
            str(tmp_path),
            "have", 
            "tree" 
        ],
    )

    assert result.exit_code == 0


def test_cli_gitignore_and_exclude(tmp_path, monkeypatch):
    """Smoke-тест CLI с флагами gitignore и exclude"""
    # создаём фиктивный .gitignore
    (tmp_path / ".gitignore").write_text("*.tmp")
    (tmp_path / "b.tmp").write_text("ignored")
    (tmp_path / "c.py").write_text("ok")

    # заглушаем тяжелые классы, чтобы не использовать pygit2
    monkeypatch.setattr(
        "spagettypy.ui.cli.GitignoreFileChecker",
        lambda *a, **kw: (lambda f: True)
    )
    monkeypatch.setattr(
        "spagettypy.ui.cli.ExcludeFileChecher",
        lambda *a, **kw: (lambda f: True)
    )

    result = runner.invoke(
        app,
        [
            "--gitignore",
            "--exclude", "*.tmp",
            "--path", str(tmp_path),"have", 
            "tree" ,
        ],
    )

    assert result.exit_code == 0
