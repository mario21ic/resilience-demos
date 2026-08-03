"""Demo: Progressive delivery con auto-rollback por SLO.

  Parte 1 — Multi-metrica: un canary con la latencia degradada, pero
            con la tasa de error perfectamente normal. Un gate que
            solo mira error rate lo promueve al 100%; uno que tambien
            mira latencia lo revierte de inmediato.
  Parte 2 — Anti-flapping: una version SANA, con ruido normal (picos
            aislados de latencia). Exigir un solo chequeo malo la
            revierte casi siempre por las dudas; exigir varios
            chequeos seguidos evita ese falso positivo.
"""
import random

from progressive_delivery import draw_metrics, run_progressive_delivery


def demo_multi_metric_gate():
    print("=" * 70)
    print("Parte 1: gate de una sola metrica vs multi-metrica")
    print("=" * 70)
    print("El canary tiene la LATENCIA degradada (p99 ~500ms vs SLO de 300ms),")
    print("pero la tasa de error se mantiene perfecta.\n")

    rng1 = random.Random(5)
    outcome_1, stage_1 = run_progressive_delivery(
        rng1, lambda r: draw_metrics(r, latency_degraded=True),
        checks_per_stage=5, required_consecutive_failures=2, check_latency=False,
    )
    print(f"  gate que SOLO mira error rate: {outcome_1} en {stage_1}% de trafico")

    rng2 = random.Random(5)
    outcome_2, stage_2 = run_progressive_delivery(
        rng2, lambda r: draw_metrics(r, latency_degraded=True),
        checks_per_stage=5, required_consecutive_failures=2, check_latency=True,
    )
    print(f"  gate que mira error rate Y latencia: {outcome_2} en {stage_2}% de trafico")

    print("\n  mirar una sola metrica deja pasar un problema real con tal de que ESA")
    print("  metrica en particular se vea bien — la latencia degradada llega al 100%")
    print("  de trafico sin que nadie la note.\n")


def demo_anti_flapping():
    print("=" * 70)
    print("Parte 2: exigir chequeos consecutivos evita reaccionar al ruido")
    print("=" * 70)
    print("Una version SANA, con picos aislados de latencia (ruido normal, 12% de")
    print("los chequeos). Se corren 2000 simulaciones independientes.\n")

    n_trials = 2000
    header = f"{'chequeos seguidos exigidos':>28} | {'rollbacks innecesarios':>24}"
    print(header)
    print("-" * len(header))
    for required in (1, 3):
        false_rollbacks = 0
        for seed in range(n_trials):
            rng = random.Random(seed)
            outcome, _ = run_progressive_delivery(
                rng, lambda r: draw_metrics(r, spike_probability=0.12),
                checks_per_stage=8, required_consecutive_failures=required,
            )
            if outcome == "rolled_back":
                false_rollbacks += 1
        print(f"{required:>28} | {false_rollbacks}/{n_trials} ({false_rollbacks / n_trials:.1%})")

    print("\n  con 1 solo chequeo malo alcanza para revertir, un pico aislado normal")
    print("  dispara un rollback INNECESARIO casi siempre. Exigiendo 3 chequeos")
    print("  seguidos, la version sana sobrevive al ruido casi todas las veces —")
    print("  sin dejar de reaccionar ante un problema real y sostenido (Parte 1).")


def main():
    demo_multi_metric_gate()
    demo_anti_flapping()


if __name__ == "__main__":
    main()
