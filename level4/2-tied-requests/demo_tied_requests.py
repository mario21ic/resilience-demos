"""Demo: Tied requests.

  Parte 1 — Por que hace falta cancelacion rapida: sin ella, cada
            request atado cuesta el doble de trabajo real siempre. Con
            una señal de cancelacion rapida entre replicas, la
            perdedora casi nunca llega a desperdiciar ejecucion.
  Parte 2 — Tied vs hedged frente a latencia de COLA (no de ejecucion):
            hedging solo reacciona pasado un umbral calibrado al
            tiempo de ejecucion; tied no necesita adivinar nada,
            porque manda a ambas replicas desde el instante cero.
"""
import random

from tied_requests import percentile, simulate_latency_comparison, simulate_wasted_work

SEED = 5
N_TRIALS = 100_000
EXEC_TIME = 10.0
HEDGE_DELAY = 15.0
CANCEL_LATENCY = 2.0


def demo_wasted_work():
    print("=" * 70)
    print("Parte 1: sin cancelacion rapida, tied cuesta el doble siempre")
    print("=" * 70)

    rng = random.Random(SEED)
    naive_avg, fast_avg = simulate_wasted_work(rng, EXEC_TIME, CANCEL_LATENCY, N_TRIALS)

    print(f"Cada request tarda {EXEC_TIME:.0f}ms en ejecutarse; la señal de cancelacion")
    print(f"entre replicas tarda {CANCEL_LATENCY:.0f}ms en propagarse.\n")
    print(f"  trabajo desperdiciado promedio SIN cancelacion: {naive_avg:.2f}ms "
          f"(siempre el 100% del tiempo de ejecucion)")
    print(f"  trabajo desperdiciado promedio CON cancelacion rapida: {fast_avg:.2f}ms")
    print(f"  -> reduccion del {100 * (1 - fast_avg / naive_avg):.1f}% en trabajo redundante\n")
    print("La mayoria de las veces, la perdedora todavia esta esperando en su propia")
    print("cola cuando le llega el aviso de cancelacion — nunca llega a ejecutar nada.\n")


def demo_latency_comparison():
    print("=" * 70)
    print("Parte 2: tied vs hedged frente a latencia de cola (no de ejecucion)")
    print("=" * 70)
    print("Cada replica tiene, la mayoria de las veces, poca cola (liviana); 10% de")
    print("las veces sufre un 'hot spot' con mucho trabajo de otros requests ya")
    print(f"encolado. Umbral de hedge calibrado al tiempo de ejecucion: {HEDGE_DELAY:.0f}ms.\n")

    rng = random.Random(SEED)
    only_a, hedged, tied, ideal = simulate_latency_comparison(rng, N_TRIALS, EXEC_TIME, HEDGE_DELAY)

    header = f"{'estrategia':>28} | {'avg':>7} | {'p50':>7} | {'p95':>7} | {'p99':>7}"
    print(header)
    print("-" * len(header))
    for name, data in (
        ("solo A (sin backup)", only_a),
        ("hedged (umbral fijo)", hedged),
        ("tied (dual + cancel rapido)", tied),
        ("ideal (oraculo)", ideal),
    ):
        d = sorted(data)
        avg = sum(d) / len(d)
        print(
            f"{name:>28} | {avg:>6.1f}ms | {percentile(d, 0.50):>6.1f}ms | "
            f"{percentile(d, 0.95):>6.1f}ms | {percentile(d, 0.99):>6.1f}ms"
        )

    print("\nTied llega practicamente al oraculo: nunca pierde tiempo esperando un")
    print("umbral, asi que aprovecha a la replica libre desde el primer instante.")
    print("Hedged mejora mucho sobre no tener backup, pero el umbral fijo le cuesta")
    print("sobre todo en el p95: son los casos donde A esta 'un poco lenta, pero no")
    print("tanto', y el hedge tarda en darse cuenta de que B ya estaba disponible.")


def main():
    demo_wasted_work()
    demo_latency_comparison()


if __name__ == "__main__":
    main()
