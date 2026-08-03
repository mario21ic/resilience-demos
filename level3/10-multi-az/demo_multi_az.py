"""Demo: Multi-AZ / multi-región con static stability.

  Parte 1 — Recuperacion dinamica vs estatica: perder una AZ cuando la
            capacidad extra ya esta corriendo (estatica) vs cuando hay
            que pedirsela al control plane, que durante un incidente
            grande esta degradado (dinamica).
  Parte 2 — La regla N-1: cuanto hay que pre-aprovisionar por AZ segun
            cuantas AZs tiene el sistema, para sobrevivir a perder
            UNA sin depender de nada mas.
  Parte 3 — Previsibilidad: la recuperacion estatica tarda siempre lo
            mismo (el tiempo de deteccion); la dinamica tiene una
            varianza enorme, porque depende del estado del control
            plane en el peor momento posible.
"""
import random

from static_stability import (
    provisioning_overhead,
    simulate_dynamic_recovery,
    simulate_static_recovery,
)

TOTAL_DEMAND = 300.0
N_AZ = 3
FAILURE_AT = 5
DETECTION_DELAY = 1
BOOT_TIME = 5
TICKS = 200


def demo_static_vs_dynamic():
    print("=" * 70)
    print("Parte 1: recuperacion estatica (pre-aprovisionada) vs dinamica")
    print("=" * 70)
    print(f"{N_AZ} AZs, demanda total = {TOTAL_DEMAND:.0f}. La AZ #1 cae en el tick {FAILURE_AT}.\n")

    static_dropped = simulate_static_recovery(
        TOTAL_DEMAND, N_AZ, capacity_fraction_per_az=0.5, failure_at=FAILURE_AT,
        detection_delay=DETECTION_DELAY, ticks=TICKS,
    )
    print(f"ESTATICA (cada AZ pre-aprovisionada al 50% de la demanda total):")
    print(f"  ticks con capacidad insuficiente: {static_dropped} — solo el tiempo que")
    print(f"  tarda el load balancer en dejar de mandar trafico a la AZ caida")
    print(f"  (una operacion de DATA PLANE, sin llamar a ninguna API).\n")

    rng = random.Random(3)
    control_plane_success_rate = 0.10
    dyn_dropped, attempts, recovered_at = simulate_dynamic_recovery(
        TOTAL_DEMAND, N_AZ, failure_at=FAILURE_AT, boot_time=BOOT_TIME,
        control_plane_success_rate=control_plane_success_rate, ticks=TICKS, rng=rng,
    )
    print(f"DINAMICA (cada AZ aprovisionada solo para su propia porcion):")
    print(f"  el control plane esta degradado por el incidente (exito por intento: "
          f"{control_plane_success_rate:.0%})")
    print(f"  intentos de scale-up necesarios: {attempts}")
    print(f"  ticks con capacidad insuficiente: {dyn_dropped}")
    print(f"  recuperada recien en el tick +{recovered_at} despues de la falla\n")


def demo_provisioning_rule():
    print("=" * 70)
    print("Parte 2: la regla N-1 de pre-aprovisionamiento")
    print("=" * 70)
    print("Cuanto tiene que aprovisionar CADA AZ para que las restantes cubran el")
    print("100% de la demanda si UNA cae, sin depender de nada mas.\n")

    header = f"{'AZs (N)':>8} | {'capacidad por AZ':>18} | {'capacidad total del sistema':>28}"
    print(header)
    print("-" * len(header))
    for n_az in (2, 3, 4, 5, 6):
        per_az = provisioning_overhead(n_az)
        total_overhead = per_az * n_az
        print(f"{n_az:>8} | {per_az:>17.1%} | {total_overhead:>26.2f}x")

    print("\nCon 2 AZs, sobrevivir a perder una implica correr el DOBLE de la capacidad")
    print("que hace falta en el dia a dia. Con 3, alcanza con un 50% extra por AZ —")
    print("por eso 3 AZs es el minimo tipico recomendado para static stability a un")
    print("costo razonable.\n")


def demo_predictability():
    print("=" * 70)
    print("Parte 3: previsibilidad — estatica es constante, dinamica es una loteria")
    print("=" * 70)
    print("30 corridas de la recuperacion DINAMICA, cada una con una 'suerte' distinta")
    print("del control plane durante el incidente.\n")

    recovery_times = []
    for seed in range(30):
        rng = random.Random(seed)
        _, _, recovered_at = simulate_dynamic_recovery(
            TOTAL_DEMAND, N_AZ, failure_at=FAILURE_AT, boot_time=BOOT_TIME,
            control_plane_success_rate=0.10, ticks=1000, rng=rng,
        )
        recovery_times.append(recovered_at)

    print(f"  recuperacion ESTATICA: siempre {DETECTION_DELAY} tick(s) — constante, sin importar nada mas.")
    print(f"  recuperacion DINAMICA: minimo {min(recovery_times)}, promedio "
          f"{sum(recovery_times) / len(recovery_times):.1f}, maximo {max(recovery_times)} ticks")
    print(f"\n  la dinamica no solo es mas lenta en promedio — es IMPREDECIBLE: no hay forma")
    print(f"  de saber de antemano si el failover va a tardar 5 ticks o 40, porque depende")
    print(f"  de que tan ocupado este el control plane justo en ese momento.")


def main():
    demo_static_vs_dynamic()
    demo_provisioning_rule()
    demo_predictability()


if __name__ == "__main__":
    main()
