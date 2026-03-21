import re
from src.models import YALexDefinition, Rule
from utils.error_handler import YALexError

# elimina comentarios (* ... *) del contenido, incluye anidados
def _strip_comments(text: str) -> str:
    result = []
    i = 0
    depth = 0
    while i < len(text):
        if text[i:i+2] == "(*":
            depth += 1
            i += 2
        elif text[i:i+2] == "*)":
            if depth == 0:
                raise YALexError("Comentario de cierre sin apertura '*)'")
            depth -= 1
            i += 2
        elif depth == 0:
            result.append(text[i])
            i += 1
        else:
            i += 1
    if depth != 0:
        raise YALexError("Comentario sin cerrar, falta '*)'")
    return "".join(result)

# extrae el contenido de la primera seccion { ... }
def _extract_braced(text: str, start: int) -> tuple[str, int]:
    if text[start] != "{":
        return "", start
    depth = 0
    i = start
    content_start = start + 1
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[content_start:i].strip(), i + 1
        i += 1
    raise YALexError("Sección sin cerrar, falta '}'")

# parsea todas las definiciones 'let ident = regexp'
def _parse_definitions(text: str) -> tuple[dict, str]:
    defs = {}
    pattern = re.compile(r'\blet\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*')
    remaining = text.strip()

    while True:
        m = pattern.match(remaining)
        if not m:
            break
        name = m.group(1)
        after_eq = remaining[m.end():]

        # la regexp termina donde empieza otro 'let' o 'rule'
        stop = re.search(r'\b(let\s+[a-zA-Z_]|rule\s+[a-zA-Z_])', after_eq)
        if stop:
            regexp = after_eq[:stop.start()].strip()
            remaining = after_eq[stop.start():]
        else:
            regexp = after_eq.strip()
            remaining = ""

        defs[name] = regexp
        if not remaining:
            break

    return defs, remaining

# encuentra el { que abre el bloque de accion, ignorando los que esten dentro de comillas
def _find_action_brace(text: str) -> int:
    in_squote = False
    in_dquote = False
    for i, c in enumerate(text):
        if in_squote:
            if c == "'":
                in_squote = False
        elif in_dquote:
            if c == '"':
                in_dquote = False
        elif c == "'":
            in_squote = True
        elif c == '"':
            in_dquote = True
        elif c == "{":
            return i
    return -1


# parsea el bloque 'rule entrypoint = regexp { action } | ...'
def _parse_rules(text: str) -> tuple[str, list[Rule]]:
    m = re.match(r'\brule\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*', text.strip())
    if not m:
        raise YALexError("No se encontró 'rule entrypoint ='")
    entrypoint = m.group(1)
    rest = text[m.end():].strip()

    rules = []
    # divide por '|' respetando llaves y corchetes
    branches = _split_branches(rest)
    for branch in branches:
        branch = branch.strip()
        if not branch:
            continue
        # separa regexp de { action }, ignorando { dentro de comillas
        action_start = _find_action_brace(branch)
        if action_start != -1:
            regexp = branch[:action_start].strip()
            action_content, _ = _extract_braced(branch, action_start)
        else:
            regexp = branch.strip()
            action_content = ""
        rules.append(Rule(pattern=regexp, action=action_content))

    return entrypoint, rules

# divide ramas por '|' sin romper dentro de [], {}, (), "" ni ''
def _split_branches(text: str) -> list[str]:
    branches = []
    current = []
    depth_brace   = 0
    depth_paren   = 0
    depth_bracket = 0
    in_dquote     = False
    in_squote     = False
    i = 0
    while i < len(text):
        c = text[i]

        if in_dquote:
            current.append(c)
            if c == '"':
                in_dquote = False
            i += 1
            continue

        if in_squote:
            current.append(c)
            # literal de un char: 'x' o '\n' — siempre cierra en la proxima comilla
            if c == "'":
                in_squote = False
            i += 1
            continue

        if c == '"':
            in_dquote = True
        elif c == "'":
            in_squote = True
        elif c == "{":
            depth_brace += 1
        elif c == "}":
            depth_brace -= 1
        elif c == "(":
            depth_paren += 1
        elif c == ")":
            depth_paren -= 1
        elif c == "[":
            depth_bracket += 1
        elif c == "]":
            depth_bracket -= 1
        elif (c == "|"
              and depth_brace == 0 and depth_paren == 0
              and depth_bracket == 0):
            branches.append("".join(current))
            current = []
            i += 1
            continue

        current.append(c)
        i += 1

    if current:
        branches.append("".join(current))
    return branches

# encuentra donde termina el bloque rule (ultima llave de cierre de accion)
# retorna el indice justo despues, o None si no hay trailer
def _find_trailer_start(text: str) -> int | None:
    # recorre de atras hacia adelante buscando el ultimo } que cierra una accion
    # el trailer seria un bloque { } completamente fuera del bloque de reglas
    # heuristica: si despues del ultimo } hay otro bloque { }, ese es el trailer
    depth = 0
    last_close = -1
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                last_close = i

    if last_close == -1:
        return None

    # busca si hay un { despues del ultimo }
    after = text[last_close + 1:].strip()
    if after.startswith("{"):
        return last_close + 1 + text[last_close + 1:].index("{")
    return None


# punto de entrada principal: parsea un archivo .yal completo
def parse_yal_file(path: str) -> YALexDefinition:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = _strip_comments(raw)
    pos = 0
    clean = clean.strip()

    header = ""
    trailer = ""

    # header opcional al inicio
    if clean.startswith("{"):
        header, pos = _extract_braced(clean, 0)
        clean = clean[pos:].strip()

    # definiciones 'let'
    defs, remaining = _parse_definitions(clean)

    # el trailer es un bloque { ... } que aparece DESPUES del bloque rule completo
    # para distinguirlo de las acciones: el trailer no esta precedido por una regexp
    # estrategia: parsea las reglas primero, luego busca trailer en lo que sobre
    entrypoint, rules = _parse_rules(remaining)

    # busca trailer: bloque { } que esta despues de la ultima accion de regla
    # se detecta si el contenido original termina con } fuera del bloque rule
    # contamos llaves para encontrar donde termina el ultimo bloque de accion
    # y si queda algo despues, ese es el trailer
    last_brace_end = _find_trailer_start(remaining)
    if last_brace_end is not None:
        trailer_text = remaining[last_brace_end:].strip()
        if trailer_text.startswith("{"):
            trailer, _ = _extract_braced(trailer_text, 0)

    return YALexDefinition(
        header=header,
        definitions=defs,
        entrypoint=entrypoint,
        rules=rules,
        trailer=trailer
    )
