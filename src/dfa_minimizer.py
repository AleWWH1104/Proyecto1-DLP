from src.models import DFAState
from utils.error_handler import YALexError

# algoritmo de Hopcroft para minimizar el DFA
def minimize_dfa(states: list[DFAState]) -> list[DFAState]:
    if not states:
        return states

    # recolecta todos los simbolos del alfabeto
    alphabet = set()
    for s in states:
        alphabet |= set(s.transitions.keys())

    # particion inicial: estados de aceptacion agrupados por token, mas no-aceptacion
    partitions: list[set] = []

    # agrupa aceptantes por token
    token_groups: dict[str, set] = {}
    non_accepting = set()
    for s in states:
        if s.is_accepting:
            token_groups.setdefault(s.token, set())
            token_groups[s.token].add(s.id)
        else:
            non_accepting.add(s.id)

    if non_accepting:
        partitions.append(non_accepting)
    for group in token_groups.values():
        partitions.append(group)

    # mapeo rapido id -> indice de particion
    def state_to_partition(sid: int) -> int:
        for i, part in enumerate(partitions):
            if sid in part:
                return i
        return -1

    # refina particiones hasta que no cambien
    changed = True
    while changed:
        changed = False
        new_partitions = []

        for part in partitions:
            if len(part) <= 1:
                new_partitions.append(part)
                continue

            # intenta dividir la particion
            groups: dict[tuple, set] = {}
            for sid in part:
                state = states[sid]
                # firma: para cada simbolo, a que particion va
                sig = tuple(
                    state_to_partition(state.transitions[a]) if a in state.transitions else -1
                    for a in sorted(alphabet)
                )
                groups.setdefault(sig, set())
                groups[sig].add(sid)

            if len(groups) > 1:
                changed = True

            new_partitions.extend(groups.values())

        partitions = new_partitions

    # construye los nuevos estados minimizados
    # representante de cada particion: el de menor id
    representatives = {}
    for i, part in enumerate(partitions):
        rep = min(part)
        for sid in part:
            representatives[sid] = rep

    # identifica el estado inicial (id=0)
    initial_rep = representatives[0]

    # construye estado minimizado por representante
    seen = set()
    new_states_map: dict[int, DFAState] = {}

    for i, part in enumerate(partitions):
        rep = min(part)
        if rep in seen:
            continue
        seen.add(rep)

        original = states[rep]
        new_transitions = {}
        for sym, dst in original.transitions.items():
            new_transitions[sym] = representatives[dst]

        new_states_map[rep] = DFAState(
            id=rep,
            positions=original.positions,
            is_accepting=original.is_accepting,
            token=original.token,
            transitions=new_transitions
        )

    # renumera estados consecutivamente, inicial primero
    old_to_new: dict[int, int] = {}
    counter = 0
    old_to_new[initial_rep] = counter
    counter += 1
    for rep in sorted(new_states_map.keys()):
        if rep != initial_rep:
            old_to_new[rep] = counter
            counter += 1

    result = []
    for old_id, new_id in sorted(old_to_new.items(), key=lambda x: x[1]):
        s = new_states_map[old_id]
        renamed_transitions = {sym: old_to_new[representatives[dst]]
                                for sym, dst in s.transitions.items()
                                if representatives[dst] in old_to_new}
        result.append(DFAState(
            id=new_id,
            positions=s.positions,
            is_accepting=s.is_accepting,
            token=s.token,
            transitions=renamed_transitions
        ))

    return result
