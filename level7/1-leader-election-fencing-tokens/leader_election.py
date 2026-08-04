"""Leader election con fencing tokens.

Varios candidatos compiten por un lock con lease (tiempo de vida),
otorgado por un servicio de coordinacion (etcd, ZooKeeper, Consul). El
que lo consigue es el lider, y tiene que RENOVARLO antes de que
expire para seguir siendolo. Si no renueva a tiempo, el lock queda
libre y otro candidato puede tomarlo — eso ES la eleccion de un nuevo
lider.

El peligro (el ejemplo clasico de Martin Kleppmann en "Designing
Data-Intensive Applications"): un lider puede quedar PAUSADO mas
tiempo del que dura su lease — una pausa larga del garbage collector,
una migracion de VM, un thread bloqueado — sin haberse caido en
realidad. Mientras esta pausado, su lease vence y otro candidato toma
el liderazgo. Cuando el proceso original se despierta, NO TIENE FORMA
de saber que paso el tiempo: sigue creyendose el lider, y puede
intentar escribir igual.

El fencing token (un numero que crece cada vez que el lock cambia de
dueño) es lo que evita que ese escritor zombie haga daño: el storage
compartido rechaza cualquier escritura con un token mas viejo que el
mas alto que ya vio, sin importar que el que escribe crea de buena fe
que sigue siendo el lider.
"""


class LeaseLock:
    """El servicio de coordinacion: un lock con lease. Cada vez que
    alguien lo adquiere (porque estaba libre, o porque el dueño
    anterior no renovo a tiempo), se entrega un fencing token nuevo,
    mayor que cualquiera anterior.
    """

    def __init__(self, ttl: float):
        self.ttl = ttl
        self.holder = None
        self.expires_at = None
        self.fencing_token = 0

    def try_acquire(self, candidate_id: str, now: float):
        if self.holder is None or now >= self.expires_at:
            self.holder = candidate_id
            self.fencing_token += 1
            self.expires_at = now + self.ttl
            return self.fencing_token
        return None  # alguien mas ya lo tiene y su lease sigue vigente

    def renew(self, candidate_id: str, now: float) -> bool:
        if self.holder == candidate_id and now < self.expires_at:
            self.expires_at = now + self.ttl
            return True
        return False


class FencedError(Exception):
    """Una escritura con un fencing token viejo: quien la manda ya no
    es el lider, aunque el todavia no lo sepa."""


class FencedStorage:
    def __init__(self):
        self._highest_token = 0
        self._data: dict = {}

    def advance_generation(self, token: int):
        """El servicio de coordinacion le avisa al storage sobre la
        nueva generacion apenas se otorga, sin esperar la primera
        escritura del nuevo lider."""
        self._highest_token = max(self._highest_token, token)

    def write(self, token: int, key: str, value):
        if token < self._highest_token:
            raise FencedError(f"token {token} es viejo (el actual es {self._highest_token})")
        self._highest_token = max(self._highest_token, token)
        self._data[key] = value

    def read(self, key: str):
        return self._data.get(key)
