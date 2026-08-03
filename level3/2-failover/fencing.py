"""Fencing por numero de generacion (epoch/term): la defensa
estructural contra split-brain.

Un health check solo puede decir "no puedo contactar al primario" —
nunca puede distinguir con certeza entre "esta muerto" y "esta vivo
pero inalcanzable desde aca" (una particion de red). Si se promueve un
standby creyendo que el primario murio, y en realidad solo estaba
particionado, quedan DOS nodos que se creen primario al mismo tiempo:
split-brain.

El fencing no evita que eso pase — evita que HAGA DANO. Cada vez que
se promueve un primario nuevo, se le asigna una generacion mayor que
la anterior. El recurso compartido (storage, servicio downstream)
solo acepta escrituras de la generacion mas alta que haya visto. Un
primario viejo que no se entero de que fue reemplazado ve sus
escrituras RECHAZADAS con un error explicito, en vez de aplicarlas
silenciosamente y corromper datos.
"""


class FencedError(Exception):
    """La escritura viene de una generacion vieja: el nodo que la
    manda ya no es el primario, aunque el todavia no lo sepa.
    """


class FencedStorage:
    def __init__(self):
        self._highest_generation = 0
        self._data: dict[str, tuple[object, int]] = {}

    def advance_generation(self, generation: int):
        """Registra una nueva generacion en el momento de la PROMOCION,
        independientemente de si el nuevo primario ya escribio algo.
        En un sistema real esto lo hace el servicio de coordinacion
        (ZooKeeper, etcd) al completar el failover, no el storage al
        recibir la primera escritura.
        """
        self._highest_generation = max(self._highest_generation, generation)

    def write(self, generation: int, key: str, value):
        if generation < self._highest_generation:
            raise FencedError(
                f"escritura rechazada: generacion {generation} es vieja "
                f"(la generacion actual es {self._highest_generation})"
            )
        self._highest_generation = max(self._highest_generation, generation)
        self._data[key] = (value, generation)

    def read(self, key: str):
        return self._data.get(key)
