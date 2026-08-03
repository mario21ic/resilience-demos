"""Demo: Canary / blue-green / rolling con criterios de promocion
automaticos.

  Parte 1 — Radio de impacto de un deploy malo, comparando las tres
            estrategias, todas con el MISMO criterio automatico (frenar
            si la tasa de error supera un umbral).
  Parte 2 — El criterio automatico en si: la misma estrategia canary,
            con y sin un chequeo automatico entre oleadas.
"""
from deployments import (
    BLUE_GREEN_STAGES,
    CANARY_STAGES,
    ROLLING_STAGES,
    simulate_rollout,
)

BAD_ERROR_RATE = 0.5   # la version nueva falla la mitad de las veces
HALT_THRESHOLD = 0.05  # se tolera hasta 5% de errores antes de frenar


def demo_blast_radius_comparison():
    print("=" * 70)
    print("Parte 1: radio de impacto de un deploy malo, por estrategia")
    print("=" * 70)
    print(f"La version nueva falla el {BAD_ERROR_RATE:.0%} de las veces. Umbral para")
    print(f"frenar automaticamente: {HALT_THRESHOLD:.0%} de errores.\n")

    header = f"{'estrategia':>12} | {'oleadas':>22} | {'expuesto al frenar':>19} | {'daño acumulado':>15}"
    print(header)
    print("-" * len(header))
    for name, stages in (("rolling", ROLLING_STAGES), ("blue-green", BLUE_GREEN_STAGES), ("canary", CANARY_STAGES)):
        exposed, damage, halted_at = simulate_rollout(stages, BAD_ERROR_RATE, HALT_THRESHOLD)
        print(f"{name:>12} | {str(stages):>22} | {exposed:>18}% | {damage:>15.1f}")

    print("\nBlue-green no tiene forma de frenar A MITAD de un despliegue: para cuando")
    print("el criterio automatico detecta el problema, el 100% del trafico ya esta")
    print("expuesto. Canary, con oleadas iniciales chicas a proposito, es la que menos")
    print("daño acumula antes de frenar.\n")


def demo_gate_value():
    print("=" * 70)
    print("Parte 2: el valor del criterio automatico en si")
    print("=" * 70)
    print("La MISMA estrategia canary, con y sin chequeo automatico entre oleadas.\n")

    exposed_gate, damage_gate, halted_gate = simulate_rollout(
        CANARY_STAGES, BAD_ERROR_RATE, HALT_THRESHOLD, use_gate=True
    )
    exposed_nogate, damage_nogate, halted_nogate = simulate_rollout(
        CANARY_STAGES, BAD_ERROR_RATE, HALT_THRESHOLD, use_gate=False
    )

    print(f"  CON criterio automatico: se frena en {halted_gate}% expuesto, "
          f"daño acumulado={damage_gate:.1f}")
    print(f"  SIN criterio (avanza en horario fijo, sin mirar metricas): "
          f"llega al {exposed_nogate}%, daño acumulado={damage_nogate:.1f}")
    print(f"\n  -> {damage_nogate / damage_gate:.0f}x mas daño sin el criterio automatico, aunque")
    print("     el PLAN de oleadas (5%, 15%, 30%, 50%, 100%) sea identico en ambos casos.")
    print("     'Desplegar de a poco' sin un chequeo real entre oleadas es solo una")
    print("     forma mas lenta de llegar al mismo desastre.")


def main():
    demo_blast_radius_comparison()
    demo_gate_value()


if __name__ == "__main__":
    main()
