from __future__ import annotations
from typing import Optional, Iterable, List, Set
import pygit2
from pathspec import PathSpec
from pathlib import Path
from ..graph import GraphProto
from .interfaces import FileChecherProto
from ..model import Relation,FileInfo, DirectoryNode

class GitFinder:
    """Ищет папку гит репозитория в текущем каталоге и выше"""
    def __init__(self) -> None:...
    
    def __call__(self, property:  str ) -> Optional[Path]:
        if isinstance(property, str):
            try:
                return Path(pygit2.discover_repository(property))
            except KeyError:
                return None


class GitignoreFileChecker:
    """Проверяет,не входит ли файл или папка в .gitignore"""
    def __init__(self, start_path: str | Path) -> None:
        if isinstance(start_path, Path):
            start_path = str(start_path)
        # Ищем путь до .git/
        git_finder = GitFinder()
        repo_path = str(git_finder(start_path))
        if not repo_path:
            self.git_repo = None
            self.repo_root = None
            return
        self.git_repo = pygit2.Repository(repo_path)
        self.repo_root = Path(repo_path).parent 
        
    def __call__(self, file: FileInfo) -> bool:
        if not self.git_repo or not self.repo_root:
            return False

        abs_path = Path(file.path) / f"{file.name}{file.format}"
        rel_path = abs_path.relative_to(self.repo_root)  
        rel_str = str(rel_path).replace("\\", "/")

        ignored = self.git_repo.path_is_ignored(rel_str)
        return not ignored
    


class GitExcludeFileChecker:
    """Проверяет, исключён ли файл локально через .git/info/exclude"""
    def __init__(self, start_path: str | Path) -> None:
        
        if isinstance(start_path, Path):
            start_path = str(start_path)
        
        git_finder = GitFinder()
        repo_path = git_finder(start_path)

        if not repo_path:
            self.git_repo = None
            self.repo_root = None
            return

        self.git_repo = pygit2.Repository(repo_path)
        self.repo_root = Path(repo_path).parent  # корень репо

        # абсолютный путь до exclude файла
        self.exclude_file:Optional[Path] = Path(repo_path) / "info" / "exclude"
        if not self.exclude_file.exists():
            self.exclude_file = None

    def __call__(self, file: FileInfo) -> bool:
        if not (self.git_repo and self.exclude_file and self.repo_root):
            return False

        abs_path = Path(file.path) / f"{file.name}{file.format}"
        rel_path = abs_path.relative_to(self.repo_root)
        rel_str = str(rel_path).replace("\\", "/")

        # .git/info/exclude обрабатывается тем же методом, что и .gitignore
        ignored = self.git_repo.path_is_ignored(rel_str)
        return ignored



class FormatFileChecker:
    """Проверяет входит ли формат в файла в поддерживаемые"""
    def __init__(self, format: str | Iterable[str]) -> None:
        
        self.support_format:Set[str] = set()
        
        if isinstance(format ,str):
            self.support_format.add(self._fix_suffix(format))

        else:
            self.support_format = set([self._fix_suffix(s) for s in format])
            
    def _is_suffix(self, suffix:str) -> bool:
        return suffix.find(".") == 0

    def _fix_suffix(self, suffix:str) -> str:
        if not self._is_suffix(suffix):
            return ".%s" % (suffix,)
        return suffix
    
    def __call__(self, file: FileInfo ) -> bool:
        if file.format:
            return file.format in self.support_format
        return False


class ExcludeFileChecher:
    "Проверяет не соответсвует ли файл или папка шаблону на исключение"
    def __init__(self, excludes: str | Iterable[str]) -> None:
        self.exlude_filter = PathSpec.from_lines("gitwildmatch",excludes)

    def __call__(self, file: FileInfo ) -> bool:
        file_path = str(Path(file.path, file.name+file.format))           
        return not self.exlude_filter.match_file(file_path)
    


class DirectoryParser:
    def __init__(self,base_path: Optional[Path] = None, checkers: Optional[Iterable[FileChecherProto]] = None) -> None:
        self.checkers = checkers
        self.base_path = base_path.resolve() if base_path else None
        self.graph:Optional[GraphProto] = None
        
        
    def _split_dirs(self, rel_path: Path) -> tuple[DirectoryNode, ...]:
        return tuple(DirectoryNode(Path(part)) for part in rel_path.parts if part not in (".", ""))    
        
    def __call__(self,graph: GraphProto, context: Path) -> GraphProto:
        all_files:List[FileInfo] = self.parse_directory(context)
        filtred_files:List[FileInfo] = self.apply_filters(files=all_files)
        self.graph = graph
        tree_map: dict[tuple[DirectoryNode, ...], list[FileInfo]] = {}

        for f in filtred_files:
            rel_dir = self._rel(f.path)
            key = self._split_dirs(rel_dir)
            tree_map.setdefault(key, []).append(f)

        # Сортируем по глубине (корни первыми)
        sorted_keys = sorted(tree_map.keys(), key=len)


        for key in sorted_keys:
            if not key:
                parent_dir = DirectoryNode(Path("."))
                current_dir = parent_dir
            else:
                current_dir = key[-1]
                parent_dir = key[-2] if len(key) > 1 else DirectoryNode(Path("."))


            if parent_dir != current_dir:
                self.graph.add_edge(parent_dir, current_dir, Relation.CONTAINS)

    
            for f in tree_map[key]:
                
                rel_file = self._rel(f.path / f"{f.name}{f.format}")
                file_node = FileInfo(
                    name=f.name,
                    format=f.format,
                    path=self._rel(f.path),
                    is_exclude=f.is_exclude,
                )
                
                if rel_file != self._rel(f.path):
                    self.graph.add_edge(current_dir, file_node, Relation.CONTAINS)

        return self.graph
    

    def _rel(self, path: Path) -> Path:
        """Возвращает относительный путь от base_path"""
        if self.base_path and path.is_absolute():
            try:
                return path.resolve().relative_to(self.base_path)
            except ValueError:
                pass
        return path
    
    
    
    def parse_directory(self, path:Path) -> List[FileInfo]:
        files:List[FileInfo]  = []
        for dirName, subdirList, fileList in path.walk():
            for file in fileList:
                filename = str(Path(file).stem)
                format = str(Path(file).suffix) 
                files.append(FileInfo(name=filename,format=format,path=dirName))
        return files
    
    def _filter(self,filecker:FileChecherProto, files:List[FileInfo]) -> List[FileInfo]:
        return list(filter(filecker.__call__,files))
    
    def apply_filters(self,files: List[FileInfo]) -> List[FileInfo]:
        if self.checkers:
            for checker in self.checkers:
                files = self._filter(checker,files)
            return list(files)
        return files
    
    
