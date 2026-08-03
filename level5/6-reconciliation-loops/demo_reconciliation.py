"""Demo: Reconciliation loops.

  Parte 1 — Imperativo (do-once) vs reconciliacion continua: ambos
            arrancan igual (3 replicas), pero solo uno sobrevive a que
            algo externo empiece a borrar pods con el tiempo.
  Parte 2 — Por nivel (level-triggered) vs por evento
            (edge-triggered): que pasa cuando los eventos que
            disparan una correccion se pierden — algo que en
            sistemas reales pasa todo el tiempo (desconexiones,
            reinicios de controlador).
"""
import random

from reconciliation import (
    DESIRED_REPLICAS,
    simulate_edge_triggered,
    simulate_imperative,
    simulate_reconciliation,
)

SEED = 2
TICKS = 200
DELETE_PROBABILITY = 0.1


def demo_imperative_vs_reconciliation():
    print("=" * 70)
    print("Parte 1: imperativo (do-once) vs reconciliacion continua")
    print("=" * 70)
    print(f"Se desean {DESIRED_REPLICAS} replicas. Cada tick, un actor externo (un nodo")
    print(f"que muere, alguien que borra un pod a mano) tiene {DELETE_PROBABILITY:.0%} de")
    print("probabilidad de eliminar una replica, sin avisarle a nadie.\n")

    rng1 = random.Random(SEED)
    h_imperative = simulate_imperative(rng1, TICKS, DELETE_PROBABILITY)
    rng2 = random.Random(SEED)
    h_reconciliation = simulate_reconciliation(rng2, TICKS, DELETE_PROBABILITY)

    print(f"  imperativo (crea 3 una vez y no vuelve a mirar):")
    print(f"    promedio de replicas activas: {sum(h_imperative) / TICKS:.2f}/{DESIRED_REPLICAS}")
    print(f"    replicas al final de la simulacion: {h_imperative[-1]}")
    print(f"  reconciliacion (compara y corrige en cada tick):")
    print(f"    promedio de replicas activas: {sum(h_reconciliation) / TICKS:.2f}/{DESIRED_REPLICAS}")
    print(f"    replicas al final de la simulacion: {h_reconciliation[-1]}")
    print("\n  el imperativo se degrada monotonamente hasta cero y se queda ahi para")
    print("  siempre; la reconciliacion se mantiene en el nivel deseado sin excepcion,")
    print("  sin importar CUANTAS veces ni POR QUE motivo se pierda una replica.\n")


def demo_level_vs_edge_triggered():
    print("=" * 70)
    print("Parte 2: por nivel vs por evento, cuando los eventos se pierden")
    print("=" * 70)
    event_drop_probability = 0.3
    print(f"Mismo escenario, pero ahora el controlador SI reacciona a cada perdida")
    print(f"de una replica — solo que el {event_drop_probability:.0%} de esos avisos se pierden")
    print("en el camino (una desconexion, un controlador que se reinicio).\n")

    rng1 = random.Random(SEED)
    h_edge = simulate_edge_triggered(rng1, TICKS, DELETE_PROBABILITY, event_drop_probability)
    rng2 = random.Random(SEED)
    h_level = simulate_reconciliation(rng2, TICKS, DELETE_PROBABILITY)

    print(f"  por evento (edge-triggered, depende de recibir el aviso):")
    print(f"    promedio: {sum(h_edge) / TICKS:.2f}/{DESIRED_REPLICAS}, final: {h_edge[-1]}")
    print(f"  por nivel (level-triggered, compara la realidad siempre):")
    print(f"    promedio: {sum(h_level) / TICKS:.2f}/{DESIRED_REPLICAS}, final: {h_level[-1]}")
    print("\n  el controlador por evento tambien se degrada hasta cero: cada evento")
    print("  perdido es una correccion que nunca sucede, y esos huecos se acumulan.")
    print("  El por nivel ni siquiera necesita saber POR QUE hay menos replicas de las")
    print("  esperadas — simplemente lo nota la proxima vez que mira, y lo corrige.")


def main():
    demo_imperative_vs_reconciliation()
    demo_level_vs_edge_triggered()


if __name__ == "__main__":
    main()
