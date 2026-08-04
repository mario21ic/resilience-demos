"""Demo: Leases y heartbeats; phi accrual failure detector.

  Parte 1 — Un detector de timeout fijo genera falsas alarmas cada vez
            que el jitter normal de la red supera el umbral, aunque el
            nodo este perfectamente sano.
  Parte 2 — El mismo historial de heartbeats, medido con phi accrual:
            se mantiene bajo durante el jitter normal, y crece sin
            limite cuando los heartbeats realmente dejan de llegar.
"""
import random

from phi_accrual import PhiAccrualDetector

FIXED_TIMEOUT = 2.0
PHI_THRESHOLD = 8.0


def demo_fixed_timeout_false_alarms():
    print("=" * 70)
    print("Parte 1: detector de timeout fijo — falsas alarmas por jitter normal")
    print("=" * 70)

    rng = random.Random(1)
    n_heartbeats = 100
    false_alarms = 0

    for _ in range(n_heartbeats):
        # 95% de las veces el heartbeat llega rapido; 5% de las veces tarda mas
        # (jitter normal de red), pero el nodo esta perfectamente sano en ambos casos
        interval = rng.uniform(0.5, 1.5) if rng.random() > 0.05 else rng.uniform(2.0, 3.0)
        if interval > FIXED_TIMEOUT:
            false_alarms += 1

    print(f"  {n_heartbeats} heartbeats de un nodo SANO, con jitter normal de red.")
    print(f"  timeout fijo de {FIXED_TIMEOUT:.0f}s: {false_alarms}/{n_heartbeats} declarados 'muerto' "
          f"por error.\n")


def demo_phi_accrual():
    print("=" * 70)
    print("Parte 2: phi accrual — se adapta al jitter, sigue detectando fallas reales")
    print("=" * 70)

    rng = random.Random(1)
    detector = PhiAccrualDetector()
    t = 0.0
    max_phi_during_healthy = 0.0

    for _ in range(100):
        interval = rng.uniform(0.5, 1.5) if rng.random() > 0.05 else rng.uniform(2.0, 3.0)
        t += interval
        phi_before_next = detector.phi(t - 0.01) if detector.last_heartbeat_time is not None else 0.0
        max_phi_during_healthy = max(max_phi_during_healthy, phi_before_next)
        detector.heartbeat(t)

    print(f"  mismo historial de 100 heartbeats sanos con jitter: phi maximo observado "
          f"= {max_phi_during_healthy:.2f} (umbral de sospecha: {PHI_THRESHOLD:.0f})")
    print(f"  -> nunca cruza el umbral: cero falsas alarmas.\n")

    print("  ahora los heartbeats de este nodo se DETIENEN por completo (falla real):")
    last_heartbeat_time = t
    for seconds_since_last in (1, 2, 3, 5, 8, 12, 20):
        phi_now = detector.phi(last_heartbeat_time + seconds_since_last)
        suspicious = " <- SOSPECHOSO" if phi_now >= PHI_THRESHOLD else ""
        print(f"    {seconds_since_last:>2}s sin heartbeat: phi={phi_now:6.2f}{suspicious}")

    print("\n  phi crece sin limite mientras no llegue ningun heartbeat mas — a diferencia")
    print("  del jitter normal (que siempre se resuelve con el proximo heartbeat), una")
    print("  falla real nunca revierte la tendencia.")


def main():
    demo_fixed_timeout_false_alarms()
    demo_phi_accrual()


if __name__ == "__main__":
    main()
