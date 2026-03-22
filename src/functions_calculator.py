from src.models import ASTNode
from utils.error_handler import YALexError

# calcula si un nodo puede generar la cadena vacia
def nullable(node: ASTNode) -> bool:
    if node is None:
        return False
    t = node.type
    if t in ("LITERAL", "CLASS", "ANY", "EOF"):
        return False
    if t == "KLEENE" or t == "OPTIONAL":
        return True
    if t == "PLUS":
        return nullable(node.left)
    if t == "UNION":
        return nullable(node.left) or nullable(node.right)
    if t == "CONCAT":
        return nullable(node.left) and nullable(node.right)
    raise YALexError(f"Tipo de nodo desconocido en nullable: {t}")

# primeras posiciones que pueden matchear el inicio de una cadena
def firstpos(node: ASTNode) -> frozenset:
    if node is None:
        return frozenset()
    t = node.type
    if t in ("LITERAL", "CLASS", "ANY", "EOF"):
        return frozenset({node.pos})
    if t in ("KLEENE", "PLUS", "OPTIONAL"):
        return firstpos(node.left)
    if t == "UNION":
        return firstpos(node.left) | firstpos(node.right)
    if t == "CONCAT":
        if nullable(node.left):
            return firstpos(node.left) | firstpos(node.right)
        return firstpos(node.left)
    raise YALexError(f"Tipo de nodo desconocido en firstpos: {t}")

# ultimas posiciones que pueden matchear el fin de una cadena
def lastpos(node: ASTNode) -> frozenset:
    if node is None:
        return frozenset()
    t = node.type
    if t in ("LITERAL", "CLASS", "ANY", "EOF"):
        return frozenset({node.pos})
    if t in ("KLEENE", "PLUS", "OPTIONAL"):
        return lastpos(node.left)
    if t == "UNION":
        return lastpos(node.left) | lastpos(node.right)
    if t == "CONCAT":
        if nullable(node.right):
            return lastpos(node.left) | lastpos(node.right)
        return lastpos(node.right)
    raise YALexError(f"Tipo de nodo desconocido en lastpos: {t}")

# construye la tabla followpos recorriendo el arbol en postorden
def build_followpos(node: ASTNode, table: dict):
    if node is None:
        return

    # primero los hijos
    build_followpos(node.left, table)
    build_followpos(node.right, table)

    t = node.type

    if t == "CONCAT":
        # para cada posicion en lastpos(left), followpos incluye firstpos(right)
        for p in lastpos(node.left):
            table.setdefault(p, set())
            table[p] |= firstpos(node.right)

    elif t in ("KLEENE", "PLUS"):
        # para cada posicion en lastpos(child), followpos incluye firstpos(child)
        for p in lastpos(node.left):
            table.setdefault(p, set())
            table[p] |= firstpos(node.left)

# recolecta todas las hojas del arbol mapeando posicion -> nodo
def collect_leaves(node: ASTNode, leaves: dict):
    if node is None:
        return
    if node.pos is not None:
        leaves[node.pos] = node
    collect_leaves(node.left, leaves)
    collect_leaves(node.right, leaves)

# calcula todo junto y retorna (followpos_table, leaves_map)
def compute_functions(root: ASTNode) -> tuple[dict, dict]:
    followpos_table = {}
    leaves = {}
    build_followpos(root, followpos_table)
    collect_leaves(root, leaves)
    return followpos_table, leaves
