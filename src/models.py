from dataclasses import dataclass, field
from typing import Optional

# representa una regla: patron -> accion
@dataclass
class Rule:
    pattern: str
    action: str

# estructura principal que sale del parser del .yal
@dataclass
class YALexDefinition:
    header: str = ""
    definitions: dict[str, str] = field(default_factory=dict)
    entrypoint: str = ""
    rules: list[Rule] = field(default_factory=list)
    trailer: str = ""

# nodo del arbol sintactico
@dataclass
class ASTNode:
    type: str           # LITERAL, UNION, CONCAT, KLEENE, PLUS, OPTIONAL, ANY, CLASS, DIFF, EOF
    value: Optional[str] = None
    left: Optional["ASTNode"] = None
    right: Optional["ASTNode"] = None
    pos: Optional[int] = None          # solo hojas
    chars: Optional[set] = None        # para CLASS y LITERAL expandido

# estado del DFA
@dataclass
class DFAState:
    id: int
    positions: frozenset
    is_accepting: bool = False
    token: Optional[str] = None        # token que acepta si is_accepting
    transitions: dict[str, int] = field(default_factory=dict)
