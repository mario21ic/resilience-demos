"""Migraciones expand/contract: durante un
[rolling deploy](../1-canary-blue-green-rolling), el codigo viejo y el
nuevo corren AL MISMO TIEMPO durante un rato — no hay un instante
unico en el que "todo" pase a la version nueva de golpe. Un cambio de
esquema destructivo hecho en un solo paso (borrar una columna y crear
otra, atomicamente) rompe a cualquier version de codigo que no
coincida exactamente con el esquema en ese instante — vieja o nueva.

La tecnica segura tiene tres pasos, nunca uno solo:

  1. EXPAND: agregar lo nuevo, sin tocar lo viejo. Ambas versiones de
     codigo pueden seguir funcionando, cada una con su propio campo.
  2. Migrar/backfill los datos existentes al campo nuevo.
  3. CONTRACT: recien cuando el 100% del codigo ya usa el campo nuevo
     (y paso una ventana de seguridad), borrar el campo viejo.

El paso destructivo se hace al final, cuando ya no puede romper a
nadie — nunca al principio ni a mitad de camino.
"""


class Schema:
    def __init__(self, columns: set):
        self.columns = set(columns)

    def has(self, column: str) -> bool:
        return column in self.columns

    def add(self, column: str):
        self.columns.add(column)

    def drop(self, column: str):
        self.columns.discard(column)


def simulate_rollout(n_instances: int, n_ticks: int, schema_events: dict):
    """Simula un rolling deploy: en cada tick, un par de instancias mas
    pasan de codigo viejo (usa la columna `email`) a codigo nuevo (usa
    `email_address`). `schema_events` mapea un tick a una funcion que
    modifica el esquema en ese momento (la migracion).

    Cada instancia, vieja o nueva, hace un request por tick contra el
    esquema actual; si la columna que espera no existe, el request
    falla. Devuelve (fallos, total_de_requests).
    """
    schema = Schema({"email"})
    new_code_count = 0
    failures = 0
    total = 0

    for t in range(n_ticks):
        if t % 2 == 0 and new_code_count < n_instances:
            new_code_count += 1

        if t in schema_events:
            schema_events[t](schema, new_code_count, n_instances)

        old_code_count = n_instances - new_code_count

        for _ in range(old_code_count):
            total += 1
            if not schema.has("email"):
                failures += 1

        for _ in range(new_code_count):
            total += 1
            if not schema.has("email_address"):
                failures += 1

    return failures, total
