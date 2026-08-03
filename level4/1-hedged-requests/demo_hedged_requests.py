"""Demo: Hedged requests (The Tail at Scale, Dean & Barroso).

  Parte 1 — La cola larga: el p50 de una replica es excelente, pero el
            p99/p999 esta dominado por un modo lento ocasional (GC,
            IO, contencion) que un promedio nunca muestra.
  Parte 2 — Hedging con umbral en el p95: cuantifica cuanto baja la
            cola al pagar una copia extra solo para el 5% de requests
            que ya se sabe que van lentos.
  Parte 3 — El tradeoff real: hedgear mas temprano (umbral mas bajo)
            mejora la cola AUN MAS, pero cuesta mucha mas carga extra
            — no hay un umbral "correcto" universal, es una perilla
            que se ajusta segun cuanta capacidad de sobra hay.
"""
import random

from hedging import hedged_call, draw_latency, percentile

N_REQUESTS = 100_000
SEED = 42


def demo_baseline_tail():
    print("=" * 70)
    print("Parte 1: la cola larga, sin hedging")
    print("=" * 70)

    rng = random.Random(SEED)
    baseline = sorted(draw_latency(rng) for _ in range(N_REQUESTS))

    print(f"{N_REQUESTS} requests contra una replica con 5% de probabilidad de un")
    print("stall lento (100-300ms) en cada llamada individual.\n")
    for p in (0.50, 0.95, 0.99, 0.999):
        print(f"  p{p * 100:>5.1f}: {percentile(baseline, p):>7.1f}ms")
    print("\nEl p50 es excelente (~10ms). El p999 esta dominado por el modo lento,")
    print("aunque solo ocurra 1 de cada 20 veces — asi es la latencia de cola.\n")

    return baseline


def demo_hedged_at_p95(baseline):
    print("=" * 70)
    print("Parte 2: hedging con umbral en el p95 observado")
    print("=" * 70)

    hedge_delay = percentile(baseline, 0.95)
    print(f"Umbral de hedge: {hedge_delay:.1f}ms (el p95 medido en la Parte 1).\n")

    rng = random.Random(SEED)
    results = [hedged_call(rng, hedge_delay) for _ in range(N_REQUESTS)]
    latencies = sorted(r[0] for r in results)
    hedge_fired = sum(1 for r in results if r[1])

    header = f"{'percentil':>10} | {'sin hedging':>12} | {'con hedging':>12}"
    print(header)
    print("-" * len(header))
    for p in (0.50, 0.95, 0.99, 0.999):
        print(f"{p * 100:>9.1f}% | {percentile(baseline, p):>10.1f}ms | {percentile(latencies, p):>10.1f}ms")

    print(f"\ncarga extra generada: {hedge_fired}/{N_REQUESTS} hedges disparados ({hedge_fired / N_REQUESTS:.1%})")
    print("el p99 baja a menos de la mitad, pagando solo 5% mas de llamadas totales.\n")


def demo_threshold_tradeoff(baseline):
    print("=" * 70)
    print("Parte 3: el tradeoff real — umbral mas bajo, mejor cola, mas carga")
    print("=" * 70)

    header = f"{'umbral':>8} | {'hedge_delay':>12} | {'carga extra':>12} | {'p99':>8} | {'p999':>8}"
    print(header)
    print("-" * len(header))
    for pct in (0.50, 0.80, 0.90, 0.95, 0.99):
        hedge_delay = percentile(baseline, pct)
        rng = random.Random(SEED)
        results = [hedged_call(rng, hedge_delay) for _ in range(N_REQUESTS)]
        latencies = sorted(r[0] for r in results)
        hedge_fired = sum(1 for r in results if r[1])
        print(
            f"p{pct * 100:>6.0f} | {hedge_delay:>10.1f}ms | {hedge_fired / N_REQUESTS:>11.1%} | "
            f"{percentile(latencies, 0.99):>6.1f}ms | {percentile(latencies, 0.999):>6.1f}ms"
        )

    print("\nHedgear en el p50 (la mitad de TODOS los requests dispara un hedge) da la")
    print("mejor cola posible, porque se le da a casi todo request una segunda chance")
    print("independiente antes de saber si iba a ser lento — pero casi duplica la")
    print("carga total. Hedgear en el p99 casi no cuesta nada, pero tampoco ayuda")
    print("mucho: para cuando se dispara, ya se espero casi todo el stall igual.")
    print("No hay un umbral 'correcto' — es una perilla que se ajusta segun cuanta")
    print("capacidad de sobra hay para pagar la carga extra.")


def main():
    baseline = demo_baseline_tail()
    demo_hedged_at_p95(baseline)
    demo_threshold_tradeoff(baseline)


if __name__ == "__main__":
    main()
