"""Read repair: cuando una lectura toca varias replicas (un quorum,
ver [level3/7-replicacion](../../level3/7-replicacion)) y estas no
estan de acuerdo, la lectura misma puede reparar a la replica atrasada
como efecto secundario — "repare al pasar", sin necesitar un proceso
aparte para ese dato puntual.
"""


class Replica:
    def __init__(self, name: str):
        self.name = name
        self.store: dict = {}  # key -> (value, version)

    def get(self, key: str):
        return self.store.get(key)

    def put(self, key: str, value, version: int):
        current = self.store.get(key)
        if current is None or version > current[1]:
            self.store[key] = (value, version)


def quorum_read_with_repair(replicas: list, key: str):
    """Lee `key` de todas las replicas dadas, determina cual version es
    la mas nueva, y repara (escribe la version mas nueva) en cualquier
    replica que estuviera atrasada.

    Devuelve (valor_mas_nuevo, nombres_de_replicas_reparadas).
    """
    responses = [(r, r.get(key)) for r in replicas]
    responses = [(r, v) for r, v in responses if v is not None]
    if not responses:
        return None, []

    newest_version = max(version for _, (_, version) in responses)
    newest_value = next(value for _, (value, version) in responses if version == newest_version)

    repaired = []
    for replica, (_, version) in responses:
        if version < newest_version:
            replica.put(key, newest_value, newest_version)
            repaired.append(replica.name)

    return newest_value, repaired
