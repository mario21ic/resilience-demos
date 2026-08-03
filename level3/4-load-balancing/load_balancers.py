"""Cinco estrategias de load balancing, cada una resolviendo una
limitacion de la anterior:

  - Round robin: reparte por turno fijo, sin mirar el estado real de
    cada backend. Falla cuando los backends no son homogeneos.
  - Least connections: elige el backend con menos requests en curso.
    Mejor que round robin con backends heterogeneos, pero "cantidad de
    conexiones" no es lo mismo que "latencia real" — un backend puede
    tener pocas conexiones y aun asi estar respondiendo lento.
  - EWMA: elige por la latencia observada reciente (promedio movil
    exponencial), reaccionando a degradacion aunque el conteo de
    conexiones todavia se vea normal.
  - P2C (power of two choices): en vez de mirar TODOS los backends
    para elegir el de menor carga, mira solo 2 al azar y elige el
    mejor de esos 2 — casi tan bueno como mirar todos, con una
    fraccion del costo por decision.
  - Consistent hashing (+ bounded loads): para trafico con AFINIDAD
    (la misma clave siempre al mismo backend, por cache locality o
    sesiones). El hashing puro puede sobrecargar un backend si una
    clave es muy popular; la variante "bounded loads" limita cuanta
    carga puede acumular cualquier backend, derivando el excedente al
    siguiente nodo del anillo.
"""
import bisect
import hashlib
import random


class RoundRobinBalancer:
    def __init__(self, n_backends: int):
        self.n_backends = n_backends
        self._next = 0

    def pick(self, loads: list) -> int:
        backend = self._next
        self._next = (self._next + 1) % self.n_backends
        return backend


class LeastConnectionsBalancer:
    """Elige el backend con menos conexiones/requests en curso. Los
    empates se rompen al azar — con desempate FIJO (ej. "el de menor
    indice"), el mismo backend gana todos los empates una y otra vez
    y termina absorbiendo mucho mas trafico del que deberia.
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    def pick(self, loads: list) -> int:
        minimum = min(loads)
        candidates = [i for i, load in enumerate(loads) if load == minimum]
        return self.rng.choice(candidates)


class EWMABalancer:
    """Elige el backend con menor latencia EWMA observada.

    `alpha` pesa cuanto importa la ultima medicion frente al
    historico: mas alto reacciona mas rapido a un cambio, pero es mas
    sensible al ruido de mediciones individuales.
    """

    def __init__(self, n_backends: int, alpha: float = 0.3, initial_latency: float = 0.0, rng: random.Random = None):
        self.alpha = alpha
        self.ewma = [initial_latency] * n_backends
        self.rng = rng or random.Random()

    def pick(self, loads: list = None) -> int:
        minimum = min(self.ewma)
        candidates = [i for i, latency in enumerate(self.ewma) if latency == minimum]
        return self.rng.choice(candidates)

    def record(self, backend: int, latency: float):
        self.ewma[backend] = self.alpha * latency + (1 - self.alpha) * self.ewma[backend]


class P2CBalancer:
    """Power of two choices: mira solo 2 backends al azar y elige el
    de menor carga entre esos 2, en vez de escanear TODOS. El costo
    por decision es O(1) en vez de O(n), y el desbalance resultante es
    sorprendentemente cercano al de escanear todos.
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    def pick(self, loads: list) -> int:
        n = len(loads)
        if n == 1:
            return 0
        i, j = self.rng.sample(range(n), 2)
        return i if loads[i] <= loads[j] else j


class ConsistentHashRing:
    """Anillo de hashing consistente clasico, sin limite de carga: cada
    backend ocupa varios puntos ("replicas virtuales") en el anillo,
    para repartir mejor el espacio de hashes entre pocos backends.
    """

    def __init__(self, backends: list, replicas: int = 100):
        self.replicas = replicas
        self.backends = list(backends)
        self.ring: list = []
        for backend in backends:
            for r in range(replicas):
                point = self._hash(f"{backend}-{r}")
                self.ring.append((point, backend))
        self.ring.sort()
        self.points = [p for p, _ in self.ring]

    @staticmethod
    def _hash(s: str) -> int:
        return int(hashlib.sha256(s.encode()).hexdigest(), 16)

    def get(self, key: str) -> str:
        point = self._hash(key)
        idx = bisect.bisect(self.points, point) % len(self.ring)
        return self.ring[idx][1]


class BoundedLoadConsistentHash:
    """Igual que `ConsistentHashRing`, pero si el backend que le toca a
    una clave ya alcanzo su carga maxima permitida
    (`promedio * balance_factor`), la clave se deriva al SIGUIENTE
    backend distinto en el anillo (probing hacia adelante), y asi
    hasta encontrar uno con lugar.

    Acota el desbalance maximo posible sin perder la afinidad de
    hashing para la gran mayoria de las claves que no son "calientes"
    — solo las que colisionan con un backend ya saturado se
    redirigen.
    """

    def __init__(self, backends: list, replicas: int = 100, balance_factor: float = 1.25):
        self.ring = ConsistentHashRing(backends, replicas)
        self.backends = list(backends)
        self.balance_factor = balance_factor
        self.load = {b: 0 for b in backends}

    def _capacity(self, total_requests_so_far: int) -> float:
        avg = total_requests_so_far / len(self.backends)
        return max(1.0, avg * self.balance_factor)

    def assign(self, key: str, total_requests_so_far: int) -> str:
        capacity = self._capacity(total_requests_so_far + 1)
        point = self.ring._hash(key)
        idx = bisect.bisect(self.ring.points, point) % len(self.ring.ring)
        n = len(self.ring.ring)

        seen = set()
        for step in range(n):
            backend = self.ring.ring[(idx + step) % n][1]
            if backend in seen:
                continue
            seen.add(backend)
            if self.load[backend] < capacity:
                self.load[backend] += 1
                return backend

        # con balance_factor >= 1 esto no deberia pasar nunca: red de seguridad
        backend = self.ring.ring[idx][1]
        self.load[backend] += 1
        return backend
