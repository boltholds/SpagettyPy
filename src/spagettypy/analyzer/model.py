from __future__ import annotations 
from dataclasses import dataclass, field 
from pathlib import Path 
from typing import List, Optional, Any, Literal
from enum import StrEnum



class Relation(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    DEFINES = "defines"
    METHODS = "methods"
    CALLINGS = "calling"
    AGREGATES = "agregates"
    ATTRACCES = "atributte acces"
    USES = "uses"
    FROM = "from"
    INHERIT = "inherit"
    ATTRIBUTE = "attribute"
    

class ClassType(StrEnum):
    NORMAL = "normal"
    ABSTRACT = "abstract"
    INTERFACE = "interface"
    DATACLASS = "dataclass"
    ENUM = "enum"
    PROTOCOL = "protocol"

class ModuleType(StrEnum):
    TEST = "test"
    SCRIPT = "script"
    CONFIG = "config"


class ImportScope(StrEnum):
    BUILTIN = "builtin"       # sys, os, math
    STDLIB = "stdlib"         # collections, pathlib
    DEPENDENCY = "dependency" # numpy, requests
    LOCAL = "local"           # твой проект
    UNKNOWN = "unknown"


class FunctionType(StrEnum):
    SYNC = "sync"
    CORUTINE = "corutine"
    ANONIME = "anonime"


class AttributionType(StrEnum):
    CONSTANT = "constant"
    NAME = "name"
    TUPLE = "tuple"
    LIST = "list"
    SET = "set"
    DICT = "dict"
    UNKNOWN = "unknown"

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
class CodeSpan:
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    source: Optional[str] = None 
    
    def __repr__(self) -> str:
        return f"{self.start_line}-{self.end_line}"   

@dataclass(slots=True,kw_only=True)  
class BaseData:     
    name: str 
    scope: ImportScope = ImportScope.UNKNOWN
    span: Optional[CodeSpan] = None
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, another):
        return hasattr(another, 'name') and self.name == another.name


@dataclass(slots=True, eq=False)
class ModuleInfo(BaseData): 
    file: Optional[FileInfo] = None 
    type: ModuleType = ModuleType.SCRIPT
    
    def __repr__(self) -> str:
        return f'Module {self.name}'
    


@dataclass(slots=True, eq=False)
class ClassInfo(BaseData):
    module: ModuleInfo
    type: ClassType = ClassType.NORMAL
    decorators: List[Any] = field(default_factory=list)

    @property
    def qualname(self) -> str:
        return f"{self.module}.{self.name}"
    
    def __repr__(self) -> str:
        return f'Class {self.name}'
    


@dataclass(slots=True, eq=False)
class FunctionInfo(BaseData):
    module: ModuleInfo
    args_types: List[str] = field(default_factory=list) # из type hints
    return_type: Optional[str] = None
    decorators: List[Any] = field(default_factory=list)
    type: FunctionType = FunctionType.SYNC
    
    @property
    def qualname(self) -> str:
        return f"{self.owner}.{self.name}" if self.owner else f"{self.module}.{self.name}"
    
    def __repr__(self) -> str:
        return f'Functions {self.name}'
        
    
@dataclass(slots=True, eq=False)
class AttributeInfo(BaseData):
    annotation: str
    value: Any
    level:str = Literal["class","instance"]
    type:AttributionType = AttributionType.UNKNOWN