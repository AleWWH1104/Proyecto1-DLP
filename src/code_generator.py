from src.models import DFAState, YALexDefinition
from utils.error_handler import YALexError

# serializa la tabla de transiciones como dict anidado Python-valido
def _build_transition_table(states: list[DFAState]) -> str:
    lines = ["TRANSITIONS = {"]
    for s in states:
        if not s.transitions:
            continue
        pairs = ", ".join(
            f"{repr(k)}: {v}" for k, v in sorted(s.transitions.items())
        )
        lines.append(f"    {s.id}: {{{pairs}}},")
    lines.append("}")
    return "\n".join(lines)

# lista de estados de aceptacion y su token
def _build_accepting_table(states: list[DFAState]) -> str:
    lines = ["ACCEPTING = {"]
    for s in states:
        if s.is_accepting:
            lines.append(f"    {s.id}: {repr(s.token)},")
    lines.append("}")
    return "\n".join(lines)

# genera el archivo lexer completo en Python
def generate_lexer(
    dfa: list[DFAState],
    definition: YALexDefinition,
    output_path: str,
    entrypoint_name: str = "gettoken"
):
    transitions = _build_transition_table(dfa)
    accepting   = _build_accepting_table(dfa)

    # acciones de cada token como diccionario
    action_lines = ["ACTIONS = {"]
    for rule in definition.rules:
        if rule.action.strip():
            # la accion es codigo arbitrario guardado como string
            action_lines.append(f"    # patron: {repr(rule.pattern[:40])}")
    action_lines.append("}")

    code = f'''# Analizador lexico generado por YALex
# No editar manualmente

{definition.header}

{transitions}

{accepting}

# retorna el lexema y el token reconocido, o lanza error lexico
def {entrypoint_name}(input_str: str, pos: int = 0):
    state = 0
    last_accepting_state = -1
    last_accepting_pos   = -1
    current_pos          = pos

    while current_pos < len(input_str):
        char = input_str[current_pos]
        if state not in TRANSITIONS or char not in TRANSITIONS[state]:
            break
        state = TRANSITIONS[state][char]
        current_pos += 1
        if state in ACCEPTING:
            last_accepting_state = state
            last_accepting_pos   = current_pos

    if last_accepting_state == -1:
        line = input_str.count('\\n', 0, pos) + 1
        end = pos
        while end < len(input_str) and input_str[end] != '\\n' and (end - pos) < 40:
            end += 1
        snippet = input_str[pos:end].rstrip()
        first_char = input_str[pos] if pos < len(input_str) else ''
        if first_char == '"':
            msg = f"LEXICAL ERROR at line {{line}}: Literal de cadena sin terminar — salto de linea o EOF dentro del string"
        elif current_pos == pos:
            msg = f"LEXICAL ERROR at line {{line}}: Caracter no reconocido {{repr(first_char)}}"
        else:
            msg = f"LEXICAL ERROR at line {{line}}: Token no reconocido {{repr(snippet)}}"
        raise LexicalError(msg)

    lexeme = input_str[pos:last_accepting_pos]
    token  = ACCEPTING[last_accepting_state]
    return token, lexeme, last_accepting_pos


# recorre todo el input y retorna lista de (token, lexema)
def tokenize(input_str: str) -> list:
    tokens = []
    pos = 0
    while pos < len(input_str):
        token, lexeme, new_pos = {entrypoint_name}(input_str, pos)
        tokens.append((token, lexeme))
        pos = new_pos
    return tokens


class LexicalError(Exception):
    pass

{definition.trailer}
'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
