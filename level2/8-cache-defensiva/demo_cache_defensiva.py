"""Demo del patron de resiliencia: Cache defensiva.

Un cache "ingenuo" (valor + TTL, recalcular al vencer) tiene tres
puntos ciegos que este demo ataca por separado:

  Parte 1 — Stale-while-revalidate: al vencer, en vez de bloquear al
            llamador mientras se refresca, se sirve el valor VIEJO de
            inmediato y se refresca en background.
  Parte 2 — Negative caching: un "no existe" tambien se cachea (con un
            TTL mas corto), para no volver a golpear al backend por
            algo que ya sabemos que no esta.
  Parte 3 — Expiracion probabilistica temprana (XFetch): en vez de que
            todos los lectores concurrentes detecten el vencimiento en
            el mismo instante exacto (disparando un cache stampede,
            ver [7-request-coalescing](../7-request-coalescing)), cada
            lectura cerca del vencimiento tiene una probabilidad
            creciente de refrescar un poco antes, sola.
"""
import random
import threading
import time

from defensive_cache import CacheWithNegativeEntries, SWRCache, should_refresh_early


# --- Parte 1: stale-while-revalidate ---------------------------------------


def demo_swr():
    print("=" * 70)
    print("Parte 1: Stale-while-revalidate")
    print("=" * 70)

    call_count = [0]

    def slow_fetch():
        call_count[0] += 1
        time.sleep(0.3)
        return f"valor #{call_count[0]}"

    cache = SWRCache(ttl=0.3, stale_ttl=1.0)

    def call(label: str):
        started = time.monotonic()
        value, source = cache.get(slow_fetch)
        elapsed = time.monotonic() - started
        print(f"  {label:<28} -> {value!r:<12} [{source}] en {elapsed:.2f}s")

    call("1) cache vacio")
    call("2) inmediatamente despues")

    time.sleep(0.35)  # supera el ttl (0.3s) pero sigue dentro de stale_ttl (1.0s)
    call("3) recien vencido (stale)")
    call("4) otro lector, stale tambien")

    time.sleep(0.35)  # deja terminar el refresh en background disparado en 3)
    call("5) despues de que termino el refresh")

    print(f"\n  llamadas reales a slow_fetch(): {call_count[0]} (una por el miss inicial, una por el refresh)")
    print("  ningun llamador esperó los 0.3s del fetch, salvo el primero (cache vacio).\n")


# --- Parte 2: negative caching ----------------------------------------------


def demo_negative_caching():
    print("=" * 70)
    print("Parte 2: Negative caching")
    print("=" * 70)

    call_count = [0]

    def lookup(key: str):
        call_count[0] += 1
        time.sleep(0.3)  # buscar y confirmar que "no existe" tambien cuesta
        return CacheWithNegativeEntries.MISSING

    print("\nSin negative caching: 5 lookups seguidos de una clave inexistente")
    call_count[0] = 0
    for i in range(5):
        started = time.monotonic()
        lookup("usuario_fantasma")
        print(f"  lookup {i + 1}: {time.monotonic() - started:.2f}s")
    print(f"  llamadas reales al backend: {call_count[0]}/5\n")

    print("Con negative caching (negative_ttl=1.0s): los mismos 5 lookups")
    call_count[0] = 0
    cache = CacheWithNegativeEntries(positive_ttl=30.0, negative_ttl=1.0)
    for i in range(5):
        started = time.monotonic()
        cache.get_or_fetch("usuario_fantasma", lookup)
        print(f"  lookup {i + 1}: {time.monotonic() - started:.2f}s")
    print(f"  llamadas reales al backend: {call_count[0]}/5")

    print("\n  esperando a que venza el negative_ttl (1.1s) para confirmar que se reintenta...")
    time.sleep(1.1)
    cache.get_or_fetch("usuario_fantasma", lookup)
    print(f"  llamadas reales al backend tras el vencimiento: {call_count[0]} (volvio a preguntar, no quedo 'perdido' para siempre)\n")


# --- Parte 3: expiracion probabilistica temprana (XFetch) -------------------


def simulate_first_trigger(expires_at: float, delta: float, beta: float, step: float, start_before: float) -> float:
    """Simula una serie de lecturas cada `step` segundos, empezando
    `start_before` segundos antes del vencimiento real, y devuelve
    cuanto antes del vencimiento se disparo el primer refresco
    (0.0 si nadie disparo antes del vencimiento exacto).
    """
    t = expires_at - start_before
    while t < expires_at:
        if should_refresh_early(t, expires_at, delta, beta):
            return expires_at - t
        t += step
    return 0.0


def demo_probabilistic_early_expiration():
    print("=" * 70)
    print("Parte 3: Expiracion probabilistica temprana (XFetch)")
    print("=" * 70)

    random.seed(11)
    expires_at = 10.0
    delta = 0.05  # recomputar este valor cuesta 50ms
    beta = 1.0
    step = 0.05  # una lectura cada 50ms
    start_before = 0.3
    n_trials = 3000

    lead_times = [simulate_first_trigger(expires_at, delta, beta, step, start_before) for _ in range(n_trials)]
    triggered_early = [lt for lt in lead_times if lt > 0]

    print(f"\n{n_trials} simulaciones independientes, lecturas cada {step * 1000:.0f}ms, "
          f"empezando {start_before:.2f}s antes del vencimiento real (delta={delta:.2f}s).\n")
    print(f"  dispararon ANTES del vencimiento exacto: {len(triggered_early)}/{n_trials} "
          f"({100 * len(triggered_early) / n_trials:.1f}%)")
    if triggered_early:
        print(f"  anticipacion minima:   {min(triggered_early):.2f}s antes del vencimiento")
        print(f"  anticipacion promedio: {sum(triggered_early) / len(triggered_early):.2f}s antes del vencimiento")
        print(f"  anticipacion maxima:   {max(triggered_early):.2f}s antes del vencimiento")
    remaining_at_deadline = n_trials - len(triggered_early)
    print(f"  llegaron sin disparar hasta el vencimiento exacto: {remaining_at_deadline}/{n_trials} "
          f"({100 * remaining_at_deadline / n_trials:.1f}%)\n")

    print("Sin esto, TODOS los lectores concurrentes detectarian el vencimiento en el")
    print("mismo instante exacto -> cache stampede (ver 7-request-coalescing). Con la")
    print("expiracion probabilistica, poco mas de la mitad dispara su refresco un poco")
    print("antes, cada uno en un momento distinto, en vez de todos exactamente al vencer.")
    print("Con un `delta` mayor (recomputar es mas caro) la anticipacion se vuelve mucho")
    print("mas agresiva: alcanza con subir delta de 0.05s a 0.3s para que practicamente")
    print("el 100% dispare antes del vencimiento exacto — es la perilla que se ajusta")
    print("segun cuanto cueste recalcular el valor real.")


def main():
    demo_swr()
    demo_negative_caching()
    demo_probabilistic_early_expiration()


if __name__ == "__main__":
    main()
