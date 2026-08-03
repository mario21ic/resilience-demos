"""Demo: Cell-based architecture — celdas de tamaño fijo y probado,
con un router delgado.

  Parte 1 — Radio de impacto constante vs creciente: en un monolito,
            una falla total siempre afecta al 100% de los clientes
            actuales, y ese 100% crece con el sistema. En una
            arquitectura por celdas, una falla total de UNA celda
            siempre afecta como maximo `cell_size` clientes, sin
            importar cuanto crezca el sistema.
  Parte 2 — Contencion de un mal deploy: desplegar celda por celda
            (canary) permite frenar un deploy malo despues de la
            primera celda, en vez de que llegue al 100% de una vez.
  Parte 3 — Asignacion estable: agregar capacidad (una celda nueva) no
            deberia reasignar a los clientes que ya estaban en celdas
            existentes — eso seria en si mismo un evento de riesgo.
"""
from cells import (
    ThinRouter,
    blast_radius_table,
    naive_mod_reassignment_fraction,
    simulate_canary_rollout,
)

CELL_SIZE = 1000


def demo_constant_blast_radius():
    print("=" * 70)
    print("Parte 1: radio de impacto constante (celdas) vs creciente (monolito)")
    print("=" * 70)
    print(f"Tamaño de celda fijo: {CELL_SIZE} clientes.\n")

    header = f"{'clientes totales':>16} | {'# celdas':>8} | {'monolito afecta':>16} | {'1 celda afecta':>16}"
    print(header)
    print("-" * len(header))
    for total, n_cells, monolith, cell, fraction in blast_radius_table([1000, 5000, 20000, 100000], CELL_SIZE):
        print(f"{total:>16} | {n_cells:>8} | {monolith:>10} (100%) | {cell:>10} ({fraction:.1%})")

    print("\nEl monolito siempre expone al 100% de sus clientes actuales a cualquier")
    print("falla total. La celda individual siempre expone, como mucho, su tamaño")
    print("fijo — a medida que el sistema crece agregando celdas, esa fraccion se")
    print("achica sola, sin ningun cambio de diseño.\n")


def demo_canary_rollout():
    print("=" * 70)
    print("Parte 2: contencion de un mal deploy con rollout celda por celda")
    print("=" * 70)

    n_cells = 20
    total_customers = n_cells * CELL_SIZE
    wave_sizes = [1, 2, 7, 10]  # 1 celda canary, despues oleadas crecientes

    print(f"{n_cells} celdas, {total_customers} clientes en total.")
    print(f"Rollout en oleadas: {wave_sizes} celdas por oleada, empezando con 1 celda canary.\n")

    monolith_affected = total_customers

    bad_affected, bad_cells = simulate_canary_rollout(n_cells, CELL_SIZE, wave_sizes, bad_deploy=True)
    good_affected, good_cells = simulate_canary_rollout(n_cells, CELL_SIZE, wave_sizes, bad_deploy=False)

    print(f"  monolito, deploy atomico al 100%:        {monolith_affected} clientes afectados si es malo")
    print(f"  cell-based, deploy MALO (se frena tras la celda canary):")
    print(f"    -> {bad_affected} clientes afectados ({bad_affected / total_customers:.1%}), "
          f"{bad_cells}/{n_cells} celdas tocadas antes de frenar")
    print(f"  cell-based, deploy BUENO (rollout completo):")
    print(f"    -> {good_affected} clientes en total ({good_affected / total_customers:.1%}), "
          f"{good_cells}/{n_cells} celdas tocadas\n")

    print("El chequeo automatico tras la celda canary (el mismo tipo de señal que")
    print("outlier detection o health checks, ver level3/3 y level3/5) es lo que")
    print("permite frenar ANTES de que el deploy malo llegue a las otras 19 celdas.\n")


def demo_stable_assignment():
    print("=" * 70)
    print("Parte 3: asignacion estable al agregar capacidad")
    print("=" * 70)

    n_customers = 10000
    customer_ids = [f"customer-{i}" for i in range(n_customers)]

    print(f"{n_customers} clientes, 10 celdas llenas. Se agrega una 11va celda")
    print("para la demanda nueva.\n")

    naive_fraction = naive_mod_reassignment_fraction(customer_ids, old_n_cells=10, new_n_cells=11)
    print(f"  particion naive (hash(cliente) % cantidad_de_celdas):")
    print(f"    -> {naive_fraction:.1%} de los clientes YA EXISTENTES cambian de celda")
    print(f"       -- cada uno de esos cambios implica migrar datos, invalidar cache,")
    print(f"       cortar conexiones en curso.\n")

    router = ThinRouter(cell_size=1000)
    for customer_id in customer_ids:
        router.assign(customer_id)
    original_assignments = {c: router.assign(c) for c in customer_ids}

    # simula el crecimiento: se agregan 1000 clientes nuevos, que van a la celda 11
    new_customers = [f"customer-new-{i}" for i in range(1000)]
    for customer_id in new_customers:
        router.assign(customer_id)

    reassigned = sum(1 for c in customer_ids if router.assign(c) != original_assignments[c])
    print(f"  router delgado (asignacion estatica, append-only):")
    print(f"    -> {reassigned}/{n_customers} clientes existentes reasignados "
          f"({reassigned / n_customers:.1%})")
    print(f"    -> los {len(new_customers)} clientes nuevos van directo a la celda "
          f"{router.n_cells - 1}, sin tocar a nadie mas.")


def main():
    demo_constant_blast_radius()
    demo_canary_rollout()
    demo_stable_assignment()


if __name__ == "__main__":
    main()
