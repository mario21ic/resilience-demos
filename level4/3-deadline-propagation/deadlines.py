"""Deadline propagation: pasar el presupuesto de latencia RESTANTE por
toda la cadena de llamadas, en vez de que cada capa aplique su propio
timeout fijo sin saber cuanto tiempo le queda realmente al cliente
original.

Sin propagacion, un timeout local (ej. "80ms para llamar al proximo
servicio") es un numero elegido a mano, desconectado de cuanto
presupuesto real le queda al request que lo origino. Con propagacion,
cada capa calcula `remaining = deadline_original - tiempo_ya_gastado`
y se lo pasa a la siguiente — y si no queda presupuesto suficiente ni
para que la proxima llamada tenga sentido, ni siquiera se la intenta.
"""
import random

ORIGINAL_DEADLINE = 100.0     # ms: lo que el cliente esta dispuesto a esperar en total
DEFAULT_LOCAL_TIMEOUT = 80.0  # ms: el timeout fijo que cada capa aplicaria SIN propagacion
MIN_USEFUL_TIME = 60.0        # ms: por debajo de esto, no vale la pena ni intentar el ultimo salto
N_HOPS = 3                    # cantidad de capas intermedias antes del salto final (el "leaf")


def draw_local_processing(rng: random.Random) -> float:
    """Cuanto tarda cada capa intermedia en su propio trabajo (con
    jitter real, no un numero fijo)."""
    return rng.uniform(5.0, 25.0)


def draw_leaf_time(rng: random.Random) -> float:
    """Cuanto tarda el salto final (el "leaf", ej. una consulta a una
    base de datos). La mayoria de las veces es rapido; 20% de las
    veces es mucho mas lento de lo normal.
    """
    if rng.random() < 0.2:
        return rng.uniform(100.0, 200.0)
    return rng.uniform(20.0, 40.0)


def call_chain_without_propagation(rng: random.Random):
    """Cada capa acumula su propio trabajo, y la llamada final se
    corta con un timeout FIJO que no tiene en cuenta cuanto ya se
    gasto ni cuanto le queda al cliente original.

    Devuelve (latencia_total, excedio_el_deadline_original, se_intento_la_llamada_final).
    """
    elapsed = sum(draw_local_processing(rng) for _ in range(N_HOPS))
    leaf_time = draw_leaf_time(rng)
    observed_leaf = min(leaf_time, DEFAULT_LOCAL_TIMEOUT)
    total = elapsed + observed_leaf
    return total, total > ORIGINAL_DEADLINE, True


def call_chain_with_propagation(rng: random.Random):
    """Cada capa calcula cuanto presupuesto REAL le queda al cliente
    original. Si ya no alcanza ni para que la llamada final tenga
    sentido, se responde de inmediato (fallback/error) sin intentarla.

    Devuelve (latencia_total, excedio_el_deadline_original, se_intento_la_llamada_final).
    """
    elapsed = sum(draw_local_processing(rng) for _ in range(N_HOPS))
    remaining = ORIGINAL_DEADLINE - elapsed
    leaf_time = draw_leaf_time(rng)

    if remaining < MIN_USEFUL_TIME:
        return elapsed, False, False

    observed_leaf = min(leaf_time, remaining)
    total = elapsed + observed_leaf
    return total, total > ORIGINAL_DEADLINE, True
