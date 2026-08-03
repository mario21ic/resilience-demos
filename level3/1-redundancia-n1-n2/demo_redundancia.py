"""Demo: Redundancia N+1 / N+2 — activo-activo vs activo-pasivo.

Dos preguntas independientes sobre como planificar redundancia:

  1) CUANTA capacidad de sobra tengo. `N` es lo que hace falta para
     cubrir la demanda normal; N+1 agrega una unidad de mas (tolera
     UNA falla simultanea sin perder capacidad); N+2 agrega dos
     (tolera DOS).
  2) COMO esta organizada esa capacidad de sobra:
       - activo-activo: todas las instancias sirven trafico todo el
         tiempo, con margen de sobra; al fallar una, las demas
         absorben su parte de inmediato, sin tiempo de reaccion.
       - activo-pasivo: una instancia sirve el 100% del trafico; las
         demas estan de guardia, sin servir nada, hasta que un
         failover (deteccion + promocion) las activa — eso toma
         tiempo, y durante ese tiempo el servicio esta CAIDO DEL TODO,
         no parcialmente degradado.

Este demo simula 2 fallas consecutivas (t=5 y t=15) sobre las cuatro
combinaciones (activo-activo/pasivo x N+1/N+2), y compara cuanto
trafico se pierde en cada una.
"""
from topology import simulate_active_active, simulate_active_passive

DEMAND = 300
CAPACITY_PER_INSTANCE = 100
FAILOVER_DELAY = 4  # ticks: deteccion + promocion del spare
TICKS = 25


def print_timeline(timeline, label):
    print(label)
    prev_dropped = None
    for tick in timeline:
        changed = tick.dropped != prev_dropped
        if tick.note or changed:
            status = f"dropped={tick.dropped}/{tick.demand}" if tick.dropped else "OK, 0 dropped"
            extra = f"  <- {tick.note}" if tick.note else ""
            print(f"  t={tick.t:>2}: capacidad={tick.capacity:>3}  {status}{extra}")
        prev_dropped = tick.dropped
    total_dropped = sum(t.dropped for t in timeline)
    print(f"  total de requests perdidos en {TICKS} ticks: {total_dropped}\n")


def main():
    print(f"Demanda constante: {DEMAND} req/tick. Fallas simuladas en t=5 y t=15.\n")

    print("=" * 70)
    print("ACTIVO-ACTIVO (todas las instancias sirven trafico todo el tiempo)")
    print("=" * 70)
    aa_n1 = simulate_active_active(
        total_instances=4, capacity_per_instance=CAPACITY_PER_INSTANCE, demand=DEMAND,
        failures={5: 1, 15: 1}, ticks=TICKS,
    )
    print_timeline(aa_n1, "N+1 (4 instancias de 100 req/tick, N=3 necesarias + 1 de sobra):")

    aa_n2 = simulate_active_active(
        total_instances=5, capacity_per_instance=CAPACITY_PER_INSTANCE, demand=DEMAND,
        failures={5: 1, 15: 1}, ticks=TICKS,
    )
    print_timeline(aa_n2, "N+2 (5 instancias, N=3 necesarias + 2 de sobra):")

    print("=" * 70)
    print("ACTIVO-PASIVO (un activo sirve el 100%, los spares estan de guardia)")
    print("=" * 70)
    ap_n1 = simulate_active_passive(
        n_spares=1, failover_delay=FAILOVER_DELAY, demand=DEMAND, failures={5, 15}, ticks=TICKS,
    )
    print_timeline(ap_n1, "N+1 (1 activo + 1 standby):")

    ap_n2 = simulate_active_passive(
        n_spares=2, failover_delay=FAILOVER_DELAY, demand=DEMAND, failures={5, 15}, ticks=TICKS,
    )
    print_timeline(ap_n2, "N+2 (1 activo + 2 standby):")

    print("Activo-activo nunca cae del todo: pierde solo la porcion de capacidad")
    print("que se cayo, y solo si ya no le alcanza para cubrir la demanda total.")
    print("Activo-pasivo pierde el 100% del trafico durante CADA failover (no hay")
    print("degradacion parcial), pero con N+2 sobrevive a la segunda falla; con")
    print("N+1, la segunda falla lo deja caido para siempre (sin mas spares).")


if __name__ == "__main__":
    main()
