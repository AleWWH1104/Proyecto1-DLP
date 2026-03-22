from utils.error_handler import YALexError

# mapa de secuencias de escape validas en yalex
ESCAPE_MAP = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "0": "\0",
    " ": " ",
}

# convierte una secuencia de escape a su caracter real
def resolve_escape(seq: str) -> str:
    if seq in ESCAPE_MAP:
        return ESCAPE_MAP[seq]
    raise YALexError(f"Secuencia de escape no reconocida: '\\{seq}'")

# parsea un literal entre comillas simples: 'a' o '\n'
def parse_char_literal(s: str) -> str:
    s = s.strip()
    if s.startswith("'") and s.endswith("'"):
        inner = s[1:-1]
        if inner.startswith("\\"):
            return resolve_escape(inner[1:])
        if len(inner) == 1:
            return inner
    raise YALexError(f"Literal de caracter invalido: {s}")

# construye un set de caracteres desde un rango c1-c2
def char_range(c1: str, c2: str) -> set:
    if ord(c1) > ord(c2):
        raise YALexError(f"Rango invalido '{c1}'-'{c2}': inicio mayor que fin")
    return {chr(c) for c in range(ord(c1), ord(c2) + 1)}

# parsea el contenido de [...] y devuelve un set de caracteres
def parse_char_class(content: str) -> set:
    chars = set()
    i = 0
    items = []

    # primero colecta todos los elementos
    while i < len(content):
        if content[i] == "\\" and i + 1 < len(content):
            items.append(resolve_escape(content[i + 1]))
            i += 2
        elif content[i] == "'":
            # literal 'x' dentro de clase
            end = content.index("'", i + 1)
            inner = content[i+1:end]
            if inner.startswith("\\"):
                items.append(resolve_escape(inner[1:]))
            else:
                items.append(inner)
            i = end + 1
        elif content[i] == '"':
            # cadena "abc" -> agrega cada caracter
            end = content.index('"', i + 1)
            for c in content[i+1:end]:
                items.append(c)
            i = end + 1
        elif content[i] in (' ', '\t'):
            # espacio entre items: separador de notacion, no caracter
            i += 1
        else:
            items.append(content[i])
            i += 1

    # ahora resuelve rangos c1 - c2
    j = 0
    while j < len(items):
        if j + 2 < len(items) and items[j + 1] == "-":
            chars |= char_range(items[j], items[j + 2])
            j += 3
        else:
            chars.add(items[j])
            j += 1

    return chars

# todos los caracteres ASCII imprimibles como representacion del '_'
def any_char_set() -> set:
    return {chr(i) for i in range(32, 127)} | {"\n", "\t", "\r"}
