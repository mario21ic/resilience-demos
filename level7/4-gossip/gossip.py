"""Gossip: como se difunde membresia (o cualquier informacion) en un
cluster grande sin un coordinador central y sin que cada nodo necesite
hablar con todos los demas.

La idea: en cada ronda, cada nodo que ya conoce una novedad se la
cuenta a un puñado de nodos elegidos AL AZAR (no a todos). La
informacion se propaga "epidemicamente" — como un rumor — y la
cantidad de nodos informados crece de forma aproximadamente
exponencial ronda a ronda, hasta cubrir todo el cluster en un numero
de rondas logaritmico respecto al tamaño total, no lineal.

Es el mecanismo detras de Cassandra (para membresia y deteccion de
fallas), Consul/Serf (protocolo SWIM), y muchos otros sistemas que
necesitan que miles de nodos converjan en la misma vista del cluster
sin un punto unico de coordinacion.
"""
import random


def simulate_gossip(n_nodes: int, rng: random.Random, failed_nodes: frozenset = frozenset(), fanout: int = 1, max_rounds: int = 30):
    """Un nodo arranca conociendo una novedad; en cada ronda, cada nodo
    informado se la cuenta a `fanout` nodos elegidos al azar entre los
    vivos. Los nodos en `failed_nodes` no participan (no informan ni
    pueden ser informados).

    Devuelve (cantidad_de_nodos_informados_por_ronda, cantidad_de_nodos_vivos).
    """
    alive = set(range(n_nodes)) - failed_nodes
    start_node = next(iter(alive))
    informed = {start_node}
    history = [len(informed)]

    for _ in range(max_rounds):
        newly_informed = set()
        for node in informed:
            targets = rng.sample(list(alive), min(fanout, len(alive)))
            newly_informed.update(targets)
        informed |= newly_informed
        history.append(len(informed))
        if len(informed) >= len(alive):
            break

    return history, len(alive)


def simulate_centralized_broadcast(n_nodes: int, coordinator: int, failed_nodes: frozenset) -> int:
    """El contraste: un coordinador central le avisa a todos de una
    vez. Si el coordinador esta entre los nodos caidos, NADIE se
    entera — no hay ningun camino alternativo.
    """
    if coordinator in failed_nodes:
        return 0
    return n_nodes - len(failed_nodes)
