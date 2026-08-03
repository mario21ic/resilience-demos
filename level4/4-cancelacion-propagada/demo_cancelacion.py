"""Demo: Cancelacion propagada.

Un pool de 10 workers procesa requests. Una dependencia se pone lenta
durante 50 ticks (t=50 a t=100), lo que hace que muchos clientes
excedan su deadline, se rindan, y reintenten (generando un request
nuevo). La pregunta: ¿que pasa con el trabajo que el cliente abandono?

  Sin cancelacion propagada: el worker sigue "atendiendo" al request
                             abandonado hasta que termina solo —
                             trabajo zombie que compite por recursos
                             con los reintentos reales.
  Con cancelacion propagada: el worker se libera en el mismo instante
                             en que el cliente se rinde.
"""
import random

from cancellation import find_recovery_tick, simulate_pileup

SEED = 4
TICKS = 2000
INCIDENT_START, INCIDENT_END = 50, 100


def main():
    print(f"Incidente: la dependencia se pone lenta de t={INCIDENT_START} a t={INCIDENT_END} "
          f"({INCIDENT_END - INCIDENT_START} ticks).\n")

    rng_no = random.Random(SEED)
    ql_no, wasted_no, useful_no, retries_no = simulate_pileup(rng_no, propagate_cancellation=False, ticks=TICKS)

    rng_yes = random.Random(SEED)
    ql_yes, wasted_yes, useful_yes, retries_yes = simulate_pileup(rng_yes, propagate_cancellation=True, ticks=TICKS)

    recovery_no = find_recovery_tick(ql_no, after=INCIDENT_END)
    recovery_yes = find_recovery_tick(ql_yes, after=INCIDENT_END)

    header = f"{'':>22} | {'cola maxima':>12} | {'worker-ticks desperdiciados':>28} | {'se recupera en el tick':>23}"
    print(header)
    print("-" * len(header))
    print(f"{'SIN cancelacion':>22} | {max(ql_no):>12} | {wasted_no:>28} | {recovery_no:>23}")
    print(f"{'CON cancelacion':>22} | {max(ql_yes):>12} | {wasted_yes:>28} | {recovery_yes:>23}")

    incident_duration = INCIDENT_END - INCIDENT_START
    print(f"\nEl incidente real duro {incident_duration} ticks. Sin cancelacion propagada, el")
    print(f"sistema tarda {recovery_no} ticks en volver a la normalidad — "
          f"{recovery_no / incident_duration:.1f}x la duracion del incidente,")
    print(f"porque el trabajo zombie (abandonado pero todavia 'en curso') sigue compitiendo")
    print(f"por los mismos workers que hacen falta para absorber los reintentos y el trafico")
    print(f"normal. Con cancelacion propagada, la recuperacion toma {recovery_yes} ticks — "
          f"{recovery_no / recovery_yes:.1f}x mas rapido.")
    print(f"\ncero trabajo desperdiciado con cancelacion propagada, contra {wasted_no} "
          f"worker-ticks tirados sin ella.")


if __name__ == "__main__":
    main()
