"""Demo: Graceful shutdown / connection draining.

  Parte 1 — SIGKILL abrupto vs SIGTERM con periodo de gracia: cuantos
            requests en curso sobreviven al apagado de una instancia.
  Parte 2 — La carrera de desregistro: el load balancer tarda un rato
            en enterarse de que la instancia se esta yendo. Un preStop
            que duerme antes de dejar de aceptar conexiones cubre esa
            ventana.
"""
import random

from graceful_shutdown import (
    draw_request_duration,
    simulate_abrupt_kill,
    simulate_deregistration_race,
    simulate_graceful_shutdown,
)

GRACE_PERIOD = 30.0


def demo_kill_vs_graceful():
    print("=" * 70)
    print("Parte 1: SIGKILL abrupto vs SIGTERM con periodo de gracia")
    print("=" * 70)

    rng = random.Random(1)
    in_flight = [draw_request_duration(rng) for _ in range(50)]

    print(f"  50 requests en curso cuando la instancia recibe la orden de apagarse")
    print(f"  (la mayoria cortos, un 10% son largos: hasta 60s).\n")

    completed_kill, dropped_kill = simulate_abrupt_kill(in_flight)
    print(f"  SIGKILL inmediato: {completed_kill} completados, {dropped_kill} perdidos")

    completed_graceful, dropped_graceful = simulate_graceful_shutdown(in_flight, GRACE_PERIOD)
    print(f"  SIGTERM + {GRACE_PERIOD:.0f}s de gracia: {completed_graceful} completados, "
          f"{dropped_graceful} perdidos")

    print(f"\n  con un periodo de gracia razonable, casi todos los requests en curso")
    print("  terminan solos con normalidad — solo se pierden los pocos que ya iban a")
    print("  tardar mas que cualquier ventana de apagado razonable.\n")


def demo_deregistration_race():
    print("=" * 70)
    print("Parte 2: la carrera de desregistro — por que existe preStop")
    print("=" * 70)

    lb_propagation_delay = 3.0
    prestop_sleep = 4.0
    print(f"  el load balancer tarda {lb_propagation_delay:.0f}s en enterarse de que la")
    print(f"  instancia se esta apagando y dejar de mandarle trafico nuevo.\n")

    rng = random.Random(2)
    failed_without, failed_with = simulate_deregistration_race(
        rng, n_requests=2000, lb_propagation_delay=lb_propagation_delay,
        prestop_sleep=prestop_sleep, arrival_window=8.0,
    )

    print(f"  SIN preStop (la app deja de aceptar conexiones en t=0): "
          f"{failed_without} requests fallidos")
    print(f"  CON preStop de {prestop_sleep:.0f}s (la app sigue aceptando un rato mas): "
          f"{failed_with} requests fallidos")

    print("\n  la app dejo de aceptar trafico exactamente cuando le llego la señal — lo")
    print("  correcto desde su punto de vista. El problema es que el LB todavia no")
    print("  sabia que debia dejar de mandarle trafico. El preStop no cambia cuando la")
    print("  app REALMENTE deja de aceptar conexiones — le da tiempo al LB a enterarse")
    print("  primero, para que ese momento coincida con la realidad.")


def main():
    demo_kill_vs_graceful()
    demo_deregistration_race()


if __name__ == "__main__":
    main()
