from utils.error_handler import YALexError

# precedencia de operadores yalex (mayor numero = mayor precedencia)
PRECEDENCE = {
    "#": 4,   # diferencia
    "*": 3,   # kleene
    "+": 3,   # positiva
    "?": 3,   # opcional
    ".": 2,   # concatenacion (operador implicito)
    "|": 1,   # union
}

UNARY_OPS = {"*", "+", "?"}
BINARY_OPS = {"|", ".", "#"}

# verifica si hay que insertar concatenacion implicita entre dos tokens
def _needs_concat(prev: str, curr: str) -> bool:
    if prev is None:
        return False
    # no inserta concat si el previo es operador binario o '('
    if prev in BINARY_OPS or prev == "(":
        return False
    # no inserta concat si el actual es operador o ')'
    if curr in BINARY_OPS or curr == ")" or curr in UNARY_OPS:
        return False
    return True

# tokeniza la expresion regular en operadores, literales y grupos
def _tokenize(expr: str) -> list:
    tokens = []
    i = 0
    while i < len(expr):
        c = expr[i]

        if c == "'" :
            # literal 'x' o '\n'
            if i + 3 < len(expr) and expr[i+1] == "\\" and expr[i+3] == "'":
                tokens.append(f"'{expr[i+1:i+3]}'")
                i += 4
            elif i + 2 < len(expr) and expr[i+2] == "'":
                tokens.append(f"'{expr[i+1]}'")
                i += 3
            else:
                raise YALexError(f"Literal de caracter mal formado en posicion {i}")

        elif c == '"':
            # cadena "abc" se trata como concatenacion de caracteres
            end = expr.index('"', i + 1)
            tokens.append(f'"{expr[i+1:end]}"')
            i = end + 1

        elif c == "[":
            # clase de caracteres [...] o [^...]
            end = expr.index("]", i + 1)
            tokens.append(expr[i:end+1])
            i = end + 1

        elif c == "_":
            tokens.append("_")
            i += 1

        elif c in ("(", ")", "|", "*", "+", "?", "#"):
            tokens.append(c)
            i += 1

        elif c == " " or c == "\t" or c == "\n":
            i += 1

        elif c.isalpha() or c == "_":
            # identificador (ya deberia estar expandido, pero por si acaso)
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            tokens.append(expr[i:j])
            i = j

        elif c == "e" and expr[i:i+3] == "eof":
            tokens.append("eof")
            i += 3

        else:
            tokens.append(c)
            i += 1

    return tokens

# algoritmo shunting yard adaptado para regex yalex
def to_postfix(expr: str) -> list:
    tokens = _tokenize(expr)

    # inserta operadores de concatenacion implicitos
    explicit = []
    for i, tok in enumerate(tokens):
        prev = explicit[-1] if explicit else None
        if _needs_concat(prev, tok):
            explicit.append(".")
        explicit.append(tok)

    output = []
    op_stack = []

    for tok in explicit:
        if tok == "(":
            op_stack.append(tok)

        elif tok == ")":
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            if not op_stack:
                raise YALexError("Parentesis sin abrir encontrado ')'")
            op_stack.pop()  # descarta '('

        elif tok in PRECEDENCE:
            # operadores unarios se manejan diferente (no hay lado izquierdo)
            while (op_stack and op_stack[-1] != "(" and
                   op_stack[-1] in PRECEDENCE and
                   PRECEDENCE[op_stack[-1]] >= PRECEDENCE[tok] and
                   tok not in UNARY_OPS):
                output.append(op_stack.pop())
            op_stack.append(tok)

        else:
            # operando: literal, clase, etc.
            output.append(tok)

    while op_stack:
        top = op_stack.pop()
        if top == "(":
            raise YALexError("Parentesis sin cerrar encontrado '('")
        output.append(top)

    return output
