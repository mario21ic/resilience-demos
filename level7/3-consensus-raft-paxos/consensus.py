"""Consenso (Raft, Paxos): como varios nodos se ponen de acuerdo sobre
UN unico lider y UNA unica secuencia de cambios de estado, incluso con
nodos que fallan o mensajes que se pierden. La pieza central de ambos
protocolos es el **quorum de mayoria simple** (`N//2 + 1` de N nodos),
usado para dos cosas distintas:

  1. Elegir lider: un candidato necesita el voto de una MAYORIA para
     ganar una eleccion.
  2. Confirmar una entrada del log: un cambio solo se considera
     "comprometido" (seguro, durable) cuando una MAYORIA de nodos ya
     lo tiene.

La razon de usar mayoria simple, y no cualquier otro numero, es una
propiedad matematica: dos subconjuntos mayoritarios de un mismo
conjunto SIEMPRE se solapan en al menos un nodo (si no se solaparan,
sus tamaños sumarian mas que el total de nodos). Esa garantia es la
que hace posible que el consenso funcione sin necesitar que todos los
nodos esten de acuerdo, ni que ninguno falle nunca.
"""
from itertools import combinations


def majority(n_nodes: int) -> int:
    return n_nodes // 2 + 1


def run_election(n_nodes: int, votes: dict):
    """Devuelve los candidatos que consiguieron una mayoria de votos
    (deberia ser, como mucho, uno solo) y el tamaño de esa mayoria.
    """
    maj = majority(n_nodes)
    winners = [candidate for candidate, count in votes.items() if count >= maj]
    return winners, maj


def all_majority_subsets(n_nodes: int):
    """Todos los subconjuntos posibles de tamaño mayoria, entre los
    `n_nodes` nodos (representados como 0..n_nodes-1)."""
    return list(combinations(range(n_nodes), majority(n_nodes)))


def is_safe_from_future_majorities(n_nodes: int, replica_set: set) -> bool:
    """Verifica si CUALQUIER subconjunto mayoritario futuro (por
    ejemplo, los votantes de la proxima eleccion) esta garantizado de
    compartir al menos un nodo con `replica_set` — la propiedad que
    hace que una entrada COMPROMETIDA (replicada a una mayoria) nunca
    se pueda perder, sin importar que nodos fallen despues.
    """
    for subset in all_majority_subsets(n_nodes):
        if not (set(subset) & replica_set):
            return False  # existe una mayoria futura que no ve esta entrada: no es segura
    return True
