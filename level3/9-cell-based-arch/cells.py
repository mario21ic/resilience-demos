"""Cell-based architecture: celdas independientes de tamaño fijo y
probado, con un router delgado que solo sabe mapear cliente -> celda.

Cada celda es una copia COMPLETA del stack (no solo un shard de
datos): su propio compute, su propia base de datos, sus propias
colas — sin dependencias compartidas con otras celdas, salvo el
router. Eso es lo que la distingue del sharding simple
(ver [8-sharding](../8-sharding)): ahi se particiona un recurso
puntual (una base de datos, un pool de workers); aca se particiona
el SERVICIO ENTERO, de punta a punta.

Tres propiedades hacen que esto sea, segun AWS, "el estado del arte"
para limitar el radio de impacto:

  1. Tamaño FIJO y PROBADO: cada celda se carga-testea a un tamaño
     conocido de antemano. Escalar el sistema es agregar MAS celdas
     de ese mismo tamaño, nunca agrandar una celda existente — asi el
     radio de impacto de una celda individual no crece con el
     sistema.
  2. Router delgado: el router no tiene logica de negocio, solo
     mapea cliente -> celda. Cuanto mas simple, menos puede fallar —
     y si falla, es la UNICA parte que puede tumbar a TODAS las
     celdas a la vez.
  3. Asignacion estable: agregar una celda nueva no debe reasignar a
     los clientes que ya estaban en celdas existentes (eso seria en
     si mismo un evento de riesgo — migrar datos, invalidar caches).
"""
import math
import zlib


def stable_hash(s: str) -> int:
    return zlib.crc32(s.encode())


class ThinRouter:
    """El router delgado: asigna cada cliente NUEVO a una celda segun
    cuantas celdas existen al momento de su alta, y nunca vuelve a
    tocar esa asignacion. No sabe nada de logica de negocio — solo
    mapea `customer_id -> cell_id`.
    """

    def __init__(self, cell_size: int):
        self.cell_size = cell_size
        self._assignments: dict = {}
        self._next_cell = 0
        self._customers_in_current_cell = 0

    def assign(self, customer_id: str) -> int:
        if customer_id in self._assignments:
            return self._assignments[customer_id]

        if self._customers_in_current_cell >= self.cell_size:
            self._next_cell += 1
            self._customers_in_current_cell = 0

        cell_id = self._next_cell
        self._assignments[customer_id] = cell_id
        self._customers_in_current_cell += 1
        return cell_id

    @property
    def n_cells(self) -> int:
        return self._next_cell + 1 if self._assignments else 0


def blast_radius_table(customer_counts: list, cell_size: int) -> list:
    """Compara el radio de impacto de una falla total en un monolito
    (siempre el 100% de los clientes actuales) contra una falla total
    de UNA celda (siempre `cell_size` clientes, como maximo), a medida
    que el sistema crece.
    """
    rows = []
    for total in customer_counts:
        n_cells = math.ceil(total / cell_size)
        monolith_blast = total
        cell_blast = min(cell_size, total)
        rows.append((total, n_cells, monolith_blast, cell_blast, cell_blast / total))
    return rows


def simulate_canary_rollout(n_cells: int, cell_size: int, wave_sizes: list, bad_deploy: bool):
    """Despliega ola por ola (`wave_sizes` = cuantas celdas nuevas se
    suman en cada ola). Si el deploy es malo, un chequeo automatico
    (outlier detection / health checks, ver level3/3 y level3/5)
    detecta el problema en la primera ola y frena el rollout antes de
    seguir. Devuelve (clientes_afectados, celdas_tocadas).
    """
    affected_customers = 0
    cells_deployed = 0
    for wave in wave_sizes:
        cells_deployed += wave
        affected_customers += wave * cell_size
        if bad_deploy:
            break
    return affected_customers, cells_deployed


def naive_mod_reassignment_fraction(customer_ids: list, old_n_cells: int, new_n_cells: int) -> float:
    """Cuantos clientes cambiarian de celda si la asignacion fuera
    `hash(cliente) % cantidad_de_celdas` (una forma comun e ingenua de
    particionar) y se agregara una celda mas.
    """
    changed = sum(
        1 for c in customer_ids if stable_hash(c) % old_n_cells != stable_hash(c) % new_n_cells
    )
    return changed / len(customer_ids)
