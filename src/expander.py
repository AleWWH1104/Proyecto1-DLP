import re
from src.models import YALexDefinition, Rule
from utils.error_handler import YALexError

# expande un identificador en su regexp recursivamente
def _expand_expr(expr: str, defs: dict, visiting: set) -> str:
    # busca tokens que sean identificadores definidos en 'let'
    token_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')

    def replace_ident(m):
        name = m.group(1)
        # palabras reservadas del lenguaje yalex, no expander
        if name in ("eof", "rule", "let"):
            return name
        if name not in defs:
            return name
        if name in visiting:
            raise YALexError(f"Dependencia circular detectada en '{name}'")
        visiting.add(name)
        expanded = _expand_expr(defs[name], defs, visiting)
        visiting.discard(name)
        return f"({expanded})"

    return token_pattern.sub(replace_ident, expr)

# expande todas las definiciones y los patrones de las reglas
def expand_definitions(definition: YALexDefinition) -> YALexDefinition:
    expanded_defs = {}

    # expande cada definicion en orden
    for name, expr in definition.definitions.items():
        expanded_defs[name] = _expand_expr(expr, definition.definitions, set())

    # expande los patrones de cada regla usando las definiciones ya expandidas
    expanded_rules = []
    for rule in definition.rules:
        expanded_pattern = _expand_expr(rule.pattern, expanded_defs, set())
        expanded_rules.append(Rule(pattern=expanded_pattern, action=rule.action))

    return YALexDefinition(
        header=definition.header,
        definitions=expanded_defs,
        entrypoint=definition.entrypoint,
        rules=expanded_rules,
        trailer=definition.trailer
    )
