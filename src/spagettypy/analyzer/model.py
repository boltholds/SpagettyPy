from __future__ import annotations 
from dataclasses import dataclass, field 
from pathlib import Path 
from typing import Dict, List, Optional, Tuple
from enum import StrEnum
from pathlib import Path

class ClassType(StrEnum):
    NORMAL = "normal"
    ABSTRACT = "abstract"
    INTERFACE = "interface"
    DATACLASS = "dataclass"
    ENUM = "enum"

class ModuleType(StrEnum):
    TEST = "test"
    SCRIPT = "script"
    CONFIG = "config"


class ImportOrigin(StrEnum):
    STDLIB = "stdlib"       # стандартная библиотека (os, sys, json, asyncio)
    THIRD_PARTY = "third_party" # внешние зависимости (numpy, requests)
    LOCAL = "local"  


@dataclass(slots=True, frozen=True) 
class FileInfo:
    name: str
    format: str
    path: Path
    is_exclude:bool = False

@dataclass(slots=True,frozen=True)
class DirectoryNode:
    path: Path    

@dataclass(slots=True) 
class ModuleInfo: 
    name: str 
    file: FileInfo 
    imports: List[str] = field(default_factory=list)
    type: ModuleType = ModuleType.SCRIPT
    scope: ImportOrigin = ImportOrigin.LOCAL

@dataclass(slots=True) 
class ClassInfo:
    name: str
    module: ModuleInfo
    bases: List[ClassInfo] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    type: ClassType = ClassType.NORMAL
    scope: ImportOrigin = ImportOrigin.LOCAL
    @property
    def qualname(self) -> str:
        return f"{self.module}.{self.name}"

@dataclass(slots=True) 
class FunctionInfo:
    name: str
    module: ModuleInfo
    owner: Optional[str] = None 
    args_types: List[str] = field(default_factory=list) # из type hints
    return_type: Optional[str] = None
    scope: ImportOrigin = ImportOrigin.LOCAL
    @property
    def qualname(self) -> str:
        return f"{self.owner}.{self.name}" if self.owner else f"{self.module}.{self.name}"