from src.models import ASTNode, DFAState
from utils.error_handler import YALexError

# genera el contenido en formato DOT para Graphviz
def _to_dot(node: ASTNode, dot_lines: list, counter: list) -> int:
    if node is None:
        return -1

    node_id = counter[0]
    counter[0] += 1

    # etiqueta segun tipo de nodo
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    if node.type in ("LITERAL", "CLASS", "ANY", "EOF"):
        val = _esc(repr(node.value or node.type))
        label = f"{node.type}\\npos={node.pos}\\n{val}"
        shape = "ellipse"
    else:
        op_labels = {
            "CONCAT": "·",
            "UNION": "|",
            "KLEENE": "*",
            "PLUS": "+",
            "OPTIONAL": "?",
        }
        label = op_labels.get(node.type, node.type)
        shape = "box"

    dot_lines.append(f'  n{node_id} [label="{label}", shape={shape}];')

    if node.left:
        left_id = _to_dot(node.left, dot_lines, counter)
        dot_lines.append(f'  n{node_id} -> n{left_id};')

    if node.right:
        right_id = _to_dot(node.right, dot_lines, counter)
        dot_lines.append(f'  n{node_id} -> n{right_id};')

    return node_id

# exporta el AST a un archivo .dot
def export_dot(root: ASTNode, output_path: str):
    lines = ["digraph AST {", '  node [fontname="Courier"];']
    _to_dot(root, lines, [0])
    lines.append("}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# exporta el AST a PNG usando graphviz (si esta instalado)
def export_png(root: ASTNode, output_path: str):
    try:
        import graphviz
    except ImportError:
        raise YALexError("graphviz no instalado. Ejecuta: pip install graphviz")

    import tempfile, os
    dot_path = output_path.replace(".png", ".dot")
    export_dot(root, dot_path)

    # llama al binario dot de graphviz
    ret = os.system(f"dot -Tpng {dot_path} -o {output_path}")
    if ret != 0:
        raise YALexError("Fallo al generar PNG. Verifica que graphviz este instalado en el sistema.")

# exporta el DFA a formato DOT — agrupa transiciones del mismo origen/destino
def export_dfa_dot(states: list[DFAState], output_path: str, title: str = "DFA"):
    lines = [
        "digraph DFA {",
        "  rankdir=LR;",
        f'  label="{title}";',
        '  node [fontname="Courier"];',
        "  __start__ [shape=point];",
    ]

    for s in states:
        if s.is_accepting:
            tok = (s.token or "").replace("return ", "").strip()
            lines.append(f'  {s.id} [shape=doublecircle label="{s.id}\\n{tok}"];')
        else:
            lines.append(f'  {s.id} [shape=circle label="{s.id}"];')

    # estado inicial siempre es 0 tras la minimizacion
    lines.append("  __start__ -> 0;")

    for s in states:
        # agrupa chars con el mismo destino en una sola arista
        grouped: dict[int, list] = {}
        for char, target in s.transitions.items():
            grouped.setdefault(target, []).append(char)
        for target, chars in grouped.items():
            sorted_chars = sorted(chars)
            if len(sorted_chars) <= 6:
                label = ", ".join(repr(c) for c in sorted_chars)
            else:
                label = ", ".join(repr(c) for c in sorted_chars[:5])
                label += f" (+{len(sorted_chars)-5})"
            label = label.replace('"', '\\"')
            lines.append(f'  {s.id} -> {target} [label="{label}"];')

    lines.append("}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# exporta el DFA a PNG usando el binario dot de graphviz
def export_dfa_png(states: list[DFAState], output_path: str, title: str = "DFA"):
    dot_path = output_path.replace(".png", ".dot")
    export_dfa_dot(states, dot_path, title)
    ret = __import__("os").system(f'dot -Tpng "{dot_path}" -o "{output_path}"')
    if ret != 0:
        raise YALexError("Fallo al generar PNG. Verifica que graphviz este instalado.")


# representacion textual del arbol (util para debug rapido)
def tree_to_str(node: ASTNode, indent: int = 0) -> str:
    if node is None:
        return ""
    prefix = "  " * indent
    if node.pos is not None:
        line = f"{prefix}{node.type}(pos={node.pos}, val={repr(node.value)})\n"
    else:
        line = f"{prefix}{node.type}\n"
    line += tree_to_str(node.left, indent + 1)
    line += tree_to_str(node.right, indent + 1)
    return line
