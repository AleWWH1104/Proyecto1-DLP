from src.models import ASTNode
from utils.char_utils import parse_char_literal, parse_char_class, any_char_set, resolve_escape
from utils.error_handler import YALexError

# contador global de posiciones para hojas
_pos_counter = 0

def _next_pos() -> int:
    global _pos_counter
    _pos_counter += 1
    return _pos_counter

def reset_positions():
    global _pos_counter
    _pos_counter = 0

# crea una hoja LITERAL con su set de caracteres y posicion
def _make_leaf(token: str) -> ASTNode:
    pos = _next_pos()

    if token == "eof":
        return ASTNode(type="EOF", value="eof", pos=pos, chars={"$eof"})

    if token == "_":
        return ASTNode(type="ANY", value="_", pos=pos, chars=any_char_set())

    if token.startswith("'") and token.endswith("'"):
        c = parse_char_literal(token)
        return ASTNode(type="LITERAL", value=c, pos=pos, chars={c})

    if token.startswith('"') and token.endswith('"'):
        # cadena: construye concatenacion de literales
        inner = token[1:-1]
        if not inner:
            raise YALexError("Cadena vacia no permitida")
        nodes = []
        i = 0
        while i < len(inner):
            if inner[i] == "\\" and i + 1 < len(inner):
                c = resolve_escape(inner[i+1])
                i += 2
            else:
                c = inner[i]
                i += 1
            p = _next_pos()
            nodes.append(ASTNode(type="LITERAL", value=c, pos=p, chars={c}))
        # reduce a arbol de concatenaciones
        result = nodes[0]
        for n in nodes[1:]:
            result = ASTNode(type="CONCAT", left=result, right=n)
        return result

    if token.startswith("[^"):
        content = token[2:-1]
        excluded = parse_char_class(content)
        all_chars = any_char_set()
        chars = all_chars - excluded
        return ASTNode(type="CLASS", value=token, pos=pos, chars=chars)

    if token.startswith("["):
        content = token[1:-1]
        chars = parse_char_class(content)
        return ASTNode(type="CLASS", value=token, pos=pos, chars=chars)

    # identificador suelto (no deberia llegar aqui si se expandio bien)
    return ASTNode(type="LITERAL", value=token, pos=pos, chars={token})

# construye el arbol desde la lista postfix
def build_ast(postfix: list) -> ASTNode:
    stack = []
    BINARY = {".", "|", "#"}
    UNARY  = {"*", "+", "?"}

    for token in postfix:
        if token in BINARY:
            if len(stack) < 2:
                raise YALexError(f"Operador binario '{token}' sin suficientes operandos")
            right = stack.pop()
            left  = stack.pop()

            if token == ".":
                stack.append(ASTNode(type="CONCAT", left=left, right=right))
            elif token == "|":
                stack.append(ASTNode(type="UNION", left=left, right=right))
            elif token == "#":
                # diferencia de conjuntos: solo valida en hojas CLASS
                if left.chars is None or right.chars is None:
                    raise YALexError("Operador '#' solo aplica entre character sets")
                diff_chars = left.chars - right.chars
                p = _next_pos()
                stack.append(ASTNode(type="CLASS", value="#", pos=p, chars=diff_chars))

        elif token in UNARY:
            if not stack:
                raise YALexError(f"Operador '{token}' sin operando")
            child = stack.pop()
            type_map = {"*": "KLEENE", "+": "PLUS", "?": "OPTIONAL"}
            stack.append(ASTNode(type=type_map[token], left=child))

        else:
            stack.append(_make_leaf(token))

    if len(stack) != 1:
        raise YALexError(f"Expresion regular mal formada, quedan {len(stack)} nodos en la pila")
    return stack[0]
