"""Replicacion: cuantas copias existen de un dato, como se mantienen
sincronizadas, y que tradeoffs de latencia/durabilidad/consistencia
implica cada estrategia.

  - Sincrona vs asincrona: el leader espera (o no) a que los
    followers confirmen antes de avisarle al cliente que el write
    tuvo exito.
  - Quorum: en vez de "todos" o "solo el leader", que se confirme un
    subconjunto W de N replicas alcanza — y si el quorum de lectura R
    se elige tal que W+R>N, toda lectura esta garantizada de ver la
    ultima escritura.
  - Leader-follower vs multi-leader: un solo punto de escritura (sin
    ambiguedad de orden) vs varios puntos de escritura independientes
    (mejor latencia/disponibilidad por region, a costa de tener que
    resolver conflictos entre escrituras concurrentes).
"""
import math


# --- Sincrona vs asincrona --------------------------------------------------


def simulate_writes(n_writes: int, write_interval: float, follower_latency: float, crash_at: float, mode: str):
    """Simula una serie de writes contra un leader que replica a sus
    followers con `follower_latency` de demora. El leader se cae en
    `crash_at`.

    mode="sync": el cliente recibe el ack recien cuando el follower ya
    confirmo -- nunca puede haber un write "acked" que no este
    replicado.
    mode="async": el cliente recibe el ack de inmediato; la
    replicacion sigue en paralelo, pudiendo quedar incompleta si el
    leader se cae antes de que termine.

    Devuelve la lista de eventos, cuales quedaron PERDIDOS (acked al
    cliente pero nunca llegaron a un follower antes del crash), y
    cuales nunca llegaron a ackearse (el cliente hubiera visto un
    error o timeout, no una falsa confirmacion).
    """
    events = []
    for i in range(n_writes):
        applied_at = i * write_interval
        replicated_at = applied_at + follower_latency
        acked_at = replicated_at if mode == "sync" else applied_at
        events.append({"id": i, "applied_at": applied_at, "acked_at": acked_at, "replicated_at": replicated_at})

    lost = [e for e in events if e["acked_at"] <= crash_at < e["replicated_at"]]
    never_acked = [e for e in events if e["acked_at"] > crash_at]
    return events, lost, never_acked


# --- Quorum ------------------------------------------------------------------


def probability_no_overlap(n: int, w: int, r: int) -> float:
    """Probabilidad de que un quorum de lectura de tamano R, elegido al
    azar entre N replicas, no comparta NINGUNA con el quorum de
    escritura de tamano W que recibio el ultimo write (tambien al
    azar). Si W+R>N, esto es matematicamente 0 -- no hay forma de
    elegir R replicas sin tocar al menos una de las W que ya
    escribieron.
    """
    if r > n - w:
        return 0.0
    return math.comb(n - w, r) / math.comb(n, r)


def empirical_stale_read_rate(n: int, w: int, r: int, trials: int, rng) -> float:
    """Version empirica de `probability_no_overlap`: elige subconjuntos
    al azar muchas veces y mide que fraccion de las lecturas no toca
    ninguna replica con el dato mas reciente.
    """
    replicas = list(range(n))
    stale = 0
    for _ in range(trials):
        write_set = set(rng.sample(replicas, w))
        read_set = set(rng.sample(replicas, r))
        if not write_set & read_set:
            stale += 1
    return stale / trials


# --- Leader-follower vs multi-leader -----------------------------------------


class LeaderFollowerCluster:
    """Todos los writes pasan por UN leader, que les asigna un numero
    de secuencia creciente segun el orden real en que los recibio. No
    hay ambiguedad posible sobre cual write es "el ultimo": el leader
    define ese orden por construccion, sin necesitar relojes de nadie.
    """

    def __init__(self):
        self._sequence = 0
        self._state = {}

    def write(self, key: str, value):
        self._sequence += 1
        self._state[key] = (value, self._sequence)
        return self._sequence

    def read(self, key: str):
        return self._state.get(key)


class MultiLeaderCluster:
    """Cada region tiene su propio leader, que acepta writes locales de
    inmediato (baja latencia, sigue funcionando aunque las otras
    regiones esten inalcanzables) y los replica de forma asincronica
    al resto. Si dos leaders reciben writes CONCURRENTES sobre la
    MISMA clave, hay un conflicto real: no hay un leader unico que
    defina el orden, asi que hace falta una regla de resolucion.

    Esta version usa "last write wins" (LWW) por timestamp local de
    cada region — la estrategia mas simple y la mas usada en
    practica, y tambien la que mas depende de que los relojes de las
    distintas regiones esten bien sincronizados entre si.
    """

    def __init__(self, regions: list):
        self.regions = regions
        self.local_state = {region: {} for region in regions}

    def write(self, region: str, key: str, value, local_timestamp: float):
        self.local_state[region][key] = (value, local_timestamp, region)

    def resolve(self, key: str):
        candidates = [state[key] for state in self.local_state.values() if key in state]
        if not candidates:
            return None, []
        winner = max(candidates, key=lambda c: c[1])
        losers = [c for c in candidates if c != winner]
        return winner, losers
