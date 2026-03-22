import os
from src.models import ASTNode
from src.parser_yalex  import parse_yal_file
from src.expander      import expand_definitions
from src.shunting_yard import to_postfix
from src.ast_builder   import build_ast, reset_positions
from src.functions_calculator import firstpos
from src.dfa_builder   import build_dfa
from src.dfa_minimizer import minimize_dfa
from src.code_generator import generate_lexer
from src.ast_visualizer import export_dot, export_dfa_dot, tree_to_str
from utils.error_handler import YALexError

BOLD  = "\033[1m"
CYAN  = "\033[96m"
RESET = "\033[0m"

def _step(n: int, msg: str):
    print(f"{BOLD}{CYAN}[{n}]{RESET} {msg}")


def _augment_with_eof_markers(rules) -> tuple[ASTNode, dict]:
    from src.ast_builder import _next_pos

    reset_positions()
    accepting_positions = {}
    combined_root = None

    for i, rule in enumerate(rules):
        postfix    = to_postfix(rule.pattern)
        branch_ast = build_ast(postfix)

        marker_pos  = _next_pos()
        marker_node = ASTNode(
            type="EOF",
            value=f"$accept_{i}",
            pos=marker_pos,
            chars={f"$accept_{i}"}
        )
        accepting_positions[marker_pos] = rule.action.strip() or f"TOKEN_{i}"

        branch = ASTNode(type="CONCAT", left=branch_ast, right=marker_node)
        combined_root = branch if combined_root is None else \
                        ASTNode(type="UNION", left=combined_root, right=branch)

    return combined_root, accepting_positions


def run_pipeline(
    yal_path:    str,
    output_path: str,
    debug:       bool = False,
    output_dir:  str  = "output"
):
    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(yal_path))[0]

    # ── Paso 1: parsear ──────────────────────────────────────
    _step(1, f"Parseando  {yal_path}")
    definition = parse_yal_file(yal_path)
    print(f"    {len(definition.rules)} reglas  |  {len(definition.definitions)} definiciones let")

    # ── Paso 2: expandir ─────────────────────────────────────
    _step(2, "Expandiendo definiciones")
    definition = expand_definitions(definition)
    if debug:
        for name, expr in definition.definitions.items():
            print(f"      {BOLD}{name}{RESET} = {expr}")

    # ── Paso 3: postfix de cada regla ────────────────────────
    _step(3, "Convirtiendo patrones a postfix")
    for rule in definition.rules:
        postfix = to_postfix(rule.pattern)
        tok     = rule.action.strip()[:30]
        print(f"      {BOLD}{tok}{RESET}")
        print(f"        regexp  : {rule.pattern[:70]}")
        print(f"        postfix : {' '.join(str(t) for t in postfix[:20])}"
              + (" ..." if len(postfix) > 20 else ""))

    # ── Paso 4: AST aumentado ────────────────────────────────
    _step(4, "Construyendo AST aumentado")
    augmented_ast, accepting_positions = _augment_with_eof_markers(definition.rules)
    if augmented_ast is None:
        raise YALexError("No se encontraron reglas en el archivo .yal")

    dot_path = os.path.join(output_dir, f"{stem}_ast.dot")
    export_dot(augmented_ast, dot_path)
    print(f"    AST -> {dot_path}")

    # ── Paso 5: DFA directo ──────────────────────────────────
    _step(5, "Construyendo DFA")
    dfa = build_dfa(augmented_ast, accepting_positions)
    print(f"    {len(dfa)} estados")

    dot_path = os.path.join(output_dir, f"{stem}_dfa.dot")
    export_dfa_dot(dfa, dot_path, title=f"{stem} DFA (sin minimizar)")
    print(f"    DFA -> {dot_path}")

    # ── Paso 6: minimizar ────────────────────────────────────
    _step(6, "Minimizando DFA (Hopcroft)")
    dfa = minimize_dfa(dfa)
    print(f"    {len(dfa)} estados")

    dot_path = os.path.join(output_dir, f"{stem}_dfa_min.dot")
    export_dfa_dot(dfa, dot_path, title=f"{stem} DFA minimizado")
    print(f"    DFA min -> {dot_path}")

    # ── Paso 7: generar código ───────────────────────────────
    _step(7, f"Generando lexer -> {output_path}")
    generate_lexer(dfa, definition, output_path, definition.entrypoint)

    return dfa, augmented_ast
