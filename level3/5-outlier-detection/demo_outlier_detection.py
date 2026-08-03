"""Demo: Outlier detection / ejection — sacar automaticamente del pool
a la replica enferma, via health checking PASIVO.

A diferencia de un health check activo (level3/3-health-check), que le
pregunta explicitamente a cada replica "¿estas sana?", el outlier
detection observa los resultados REALES del trafico que ya se esta
mandando y saca del pool a la que se comporta peor que sus pares — sin
necesidad de un endpoint de health check dedicado, y reaccionando tan
rapido como llegan los propios requests.

  Parte 1 — Ejeccion por fallas consecutivas, con backoff: una replica
            que falla una racha de veces se saca del pool por un
            tiempo; si vuelve a fallar apenas se la reincorpora, la
            proxima ejeccion dura mas — evita que una replica que
            "flapea" entre y salga del pool sin parar. Una falla
            aislada, en cambio, no dispara nada.
  Parte 2 — Deteccion estadistica (tasa de exito): entre varias
            replicas con trafico real, la que tiene una tasa de exito
            muy por debajo del resto del pool se identifica y se
            eyecta, sin necesitar un umbral fijo definido a mano.
  Parte 3 — La red de seguridad: nunca eyectar mas de una fraccion del
            pool de una vez. Cuando MUCHAS replicas lucen mal al mismo
            tiempo, lo mas probable es un problema compartido (una
            dependencia comun caida) — eyectarlas a todas dejaria cero
            capacidad en vez de proteger algo.
"""
import random

from outlier_detector import ConsecutiveFailureEjector, SuccessRateOutlierDetector


# --- Parte 1: fallas consecutivas + backoff de ejeccion --------------------


def demo_consecutive_failures():
    print("=" * 70)
    print("Parte 1: ejeccion por fallas consecutivas, con backoff")
    print("=" * 70)
    print("Una replica 'flapper' falla en rachas de 5, se recupera brevemente al")
    print("volver al pool, y vuelve a fallar — 4 veces seguidas.\n")

    ejector = ConsecutiveFailureEjector(consecutive_failures_threshold=5, base_ejection_time=5, max_ejection_time=60)

    t = 0
    for wave in range(1, 5):
        while ejector.is_ejected("flapper", t):
            t += 1
        for _ in range(5):
            if ejector.record_result("flapper", ok=False, now=t):
                until = ejector.ejected_until("flapper")
                print(f"  t={t:>3}: ejectada (ola {wave}) hasta t={until} (duracion: {until - t} ticks)")
            t += 1

    print("\nUna replica distinta tiene un blip aislado de solo 2 fallas seguidas:")
    ejector2 = ConsecutiveFailureEjector(consecutive_failures_threshold=5)
    t2 = 0
    for _ in range(2):
        ejector2.record_result("blip", ok=False, now=t2)
        t2 += 1
    ejector2.record_result("blip", ok=True, now=t2)
    print(f"  fue ejectada? {ejector2.is_ejected('blip', t2)} (2 fallas no alcanzan el umbral de 5)\n")


# --- Parte 2: deteccion estadistica (tasa de exito) -----------------------


def run_pool(success_rates: dict, n_requests: int, seed: int, stdev_factor: float, max_ejection_fraction: float):
    rng = random.Random(seed)
    detector = SuccessRateOutlierDetector(
        window_size=200, min_requests=100, stdev_factor=stdev_factor, max_ejection_fraction=max_ejection_fraction
    )
    for backend, rate in success_rates.items():
        for _ in range(n_requests):
            detector.record_result(backend, rng.random() < rate)
    return detector.compute_ejections(), {b: detector.success_rate(b) for b in success_rates}


def demo_statistical_outlier():
    print("=" * 70)
    print("Parte 2: deteccion estadistica por tasa de exito")
    print("=" * 70)
    print("9 replicas sanas (~98% de exito) + 1 con un problema propio (~60%).\n")

    rates = {f"ok{i}": 0.98 for i in range(9)}
    rates["bad"] = 0.60
    ejected, observed = run_pool(rates, n_requests=200, seed=1, stdev_factor=0.8, max_ejection_fraction=0.34)

    for backend, rate in sorted(observed.items(), key=lambda kv: kv[1]):
        marker = " <- EJECTADA" if backend in ejected else ""
        print(f"  {backend:>6}: {rate:.0%} de exito{marker}")
    print(f"\n  ejectadas: {ejected} — identificada sin necesitar un umbral fijo definido")
    print("  a mano, solo comparando cada replica contra el resto del pool.\n")


# --- Parte 3: la red de seguridad (max ejection fraction) -----------------


def demo_max_ejection_fraction():
    print("=" * 70)
    print("Parte 3: la red de seguridad — nunca eyectar mas de una fraccion del pool")
    print("=" * 70)
    print("4 replicas sanas (~98%) + 6 con un problema COMPARTIDO (~75%, ej. una")
    print("dependencia comun degradada) — no son 6 fallas independientes.\n")

    rates = {f"ok{i}": 0.98 for i in range(4)}
    rates.update({f"bad{i}": 0.75 for i in range(6)})

    ejected_nocap, observed = run_pool(rates, n_requests=200, seed=2, stdev_factor=0.8, max_ejection_fraction=1.0)
    ejected_cap, _ = run_pool(rates, n_requests=200, seed=2, stdev_factor=0.8, max_ejection_fraction=0.34)

    for backend, rate in sorted(observed.items(), key=lambda kv: kv[1]):
        marker = ""
        if backend in ejected_nocap:
            marker = " <- eyectada SIN cap"
        if backend in ejected_cap:
            marker += " <- eyectada CON cap 34%"
        print(f"  {backend:>6}: {rate:.0%} de exito{marker}")

    print(f"\n  sin cap: {len(ejected_nocap)}/10 replicas eyectadas ({sorted(ejected_nocap)})")
    print(f"  con cap del 34%: {len(ejected_cap)}/10 replicas eyectadas ({sorted(ejected_cap)})")
    print("\n  el cap frena la ejeccion en 3 replicas en vez de 4: cuando gran parte del")
    print("  pool luce mal a la vez, seguir eyectando no arregla la causa compartida —")
    print("  solo reduce la capacidad que queda para absorber el trafico restante.")


def main():
    demo_consecutive_failures()
    demo_statistical_outlier()
    demo_max_ejection_fraction()


if __name__ == "__main__":
    main()
