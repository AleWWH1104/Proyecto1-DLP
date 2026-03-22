from collections import deque
from src.models import ASTNode, DFAState
from src.functions_calculator import firstpos, compute_functions
from utils.error_handler import YALexError

# construye el DFA directo a partir de un arbol con marcadores de aceptacion
# accepting_positions: dict pos -> token_name (que token acepta esa posicion)
def build_dfa(root: ASTNode, accepting_positions: dict[int, str]) -> list[DFAState]:
    followpos, leaves = compute_functions(root)

    # estado inicial: firstpos de la raiz
    initial = firstpos(root)
    if not initial:
        raise YALexError("La expresion regular no genera ninguna posicion inicial")

    states: dict[frozenset, DFAState] = {}
    queue = deque()

    def get_or_create(positions: frozenset) -> DFAState:
        if positions in states:
            return states[positions]

        state_id = len(states)

        # determina si es de aceptacion y que token acepta
        # si hay multiples tokens posibles, prioriza el de menor posicion (orden de definicion)
        token = None
        accepting = False
        for pos in sorted(positions):
            if pos in accepting_positions:
                accepting = True
                token = accepting_positions[pos]
                break

        state = DFAState(id=state_id, positions=positions,
                         is_accepting=accepting, token=token)
        states[positions] = state
        queue.append(state)
        return state

    get_or_create(initial)

    while queue:
        current = queue.popleft()

        # agrupa posiciones por el caracter que consumen
        symbol_to_positions: dict[str, set] = {}
        for pos in current.positions:
            if pos not in leaves:
                continue
            leaf = leaves[pos]
            if leaf.chars is None:
                continue
            for char in leaf.chars:
                symbol_to_positions.setdefault(char, set())
                symbol_to_positions[char] |= followpos.get(pos, set())

        # crea transiciones
        for symbol, next_positions in symbol_to_positions.items():
            if not next_positions:
                continue
            next_state = get_or_create(frozenset(next_positions))
            current.transitions[symbol] = next_state.id

    return list(states.values())
