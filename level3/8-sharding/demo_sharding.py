"""Demo: Sharding / partitioning, y sobre todo shuffle sharding.

  Parte 1 — Sharding simple: un tenant toxico degrada su shard, y con
            el a todos los que lo comparten.
  Parte 2 — Shuffle sharding: la misma situacion, pero cada tenant
            tiene una COMBINACION de shards en vez de uno solo — se
            cuantifica cuanto se reduce el blast radius.
  Parte 3 — Por que funciona con pocos shards fisicos: la explosion
            combinatoria de C(N, K).
  Parte 4 — El cierre con retry: un tenant que comparte solo UNO de
            sus shards con los toxicos se recupera solo con reintentar
            contra el otro shard de su propia combinacion.
"""
import random

from sharding import (
    assign_shuffle_shards,
    assign_single_shard,
    blast_radius,
    succeeds_with_retry,
    theoretical_full_overlap_probability,
)

N_TENANTS = 10000
N_SHARDS = 8
K = 2


def demo_single_shard():
    print("=" * 70)
    print("Parte 1: sharding simple — un shard toxico afecta a todo el que lo comparte")
    print("=" * 70)

    rng = random.Random(7)
    assignment = assign_single_shard(N_TENANTS, N_SHARDS, rng)
    toxic_shard = 3

    affected = sum(1 for s in assignment if s == toxic_shard)
    print(f"{N_TENANTS} tenants repartidos en {N_SHARDS} shards (1 shard por tenant).")
    print(f"El shard #{toxic_shard} se degrada por un tenant toxico.\n")
    print(f"  tenants 100% afectados: {affected}/{N_TENANTS} ({affected / N_TENANTS:.1%})")
    print(f"  — cualquier tenant que haya caido en ese shard, sin excepcion.\n")


def demo_shuffle_sharding():
    print("=" * 70)
    print("Parte 2: shuffle sharding — cada tenant tiene una COMBINACION de shards")
    print("=" * 70)

    rng = random.Random(7)
    combos = assign_shuffle_shards(N_TENANTS, N_SHARDS, K, rng)
    toxic_shards = {2, 5}  # los K shards que el tenant toxico logro degradar (los SUYOS)

    result = blast_radius(combos, toxic_shards)
    theoretical = theoretical_full_overlap_probability(N_SHARDS, K, len(toxic_shards))

    print(f"Los mismos {N_TENANTS} tenants, ahora cada uno con una combinacion de {K}")
    print(f"shards de {N_SHARDS} posibles. El tenant toxico degrada sus propios {K} shards")
    print(f"({sorted(toxic_shards)}).\n")
    print(f"  100% afectados (su combinacion ES exactamente la toxica): "
          f"{result['full']}/{N_TENANTS} ({result['full'] / N_TENANTS:.1%})")
    print(f"  parcialmente afectados (comparten 1 de {K}):                 "
          f"{result['partial']}/{N_TENANTS} ({result['partial'] / N_TENANTS:.1%})")
    print(f"  no afectados en absoluto:                                    "
          f"{result['none']}/{N_TENANTS} ({result['none'] / N_TENANTS:.1%})")
    print(f"\n  probabilidad teorica de coincidencia exacta: {theoretical:.1%} "
          f"(coincide con lo medido)")
    print(f"  el blast radius total baja de ~12.5% (Parte 1) a ~{theoretical:.1%} — sin")
    print(f"  agregar NINGUN shard fisico nuevo, solo cambiando como se asignan.\n")


def demo_combinatorial_explosion():
    print("=" * 70)
    print("Parte 3: por que funciona con pocos shards fisicos")
    print("=" * 70)
    print("La cantidad de combinaciones distintas de tamano K entre N shards es")
    print("C(N, K) — crece mucho mas rapido que N.\n")

    import math

    header = f"{'N (shards fisicos)':>20} | {'K (por tenant)':>15} | {'combinaciones distintas':>24}"
    print(header)
    print("-" * len(header))
    for n, k in ((8, 2), (8, 3), (16, 2), (16, 4), (32, 4)):
        print(f"{n:>20} | {k:>15} | {math.comb(n, k):>24}")
    print("\nCon 32 shards fisicos y combinaciones de 4, hay casi 36 mil 'carriles'")
    print("virtuales distintos — mucho mas aislamiento del que cualquier cantidad")
    print("razonable de shards fisicos podria dar por si sola.\n")


def demo_retry_closes_the_loop():
    print("=" * 70)
    print("Parte 4: el cierre con retry — recuperar a los parcialmente afectados")
    print("=" * 70)

    rng = random.Random(7)
    combos = assign_shuffle_shards(N_TENANTS, N_SHARDS, K, rng)
    toxic_shards = {2, 5}

    # sin retry: solo se prueba el primer shard de la combinacion del tenant
    success_no_retry = sum(1 for combo in combos if combo[0] not in toxic_shards)
    # con retry: si el primero falla, se prueba el resto de la combinacion propia
    success_with_retry = sum(1 for combo in combos if succeeds_with_retry(combo, toxic_shards))

    print("Un cliente que solo prueba el primer shard de su combinacion (sin retry)")
    print(f"vs uno que reintenta contra el resto de SU PROPIA combinacion:\n")
    print(f"  sin retry entre los shards del tenant: {success_no_retry}/{N_TENANTS} "
          f"exitosos ({success_no_retry / N_TENANTS:.1%})")
    print(f"  con retry al resto de su combinacion:  {success_with_retry}/{N_TENANTS} "
          f"exitosos ({success_with_retry / N_TENANTS:.1%})")
    print("\n  el retry (level1/2-retry) recupera a todos los 'parcialmente afectados'")
    print("  de la Parte 2 — solo quedan afuera los que comparten la combinacion")
    print("  EXACTA con el tenant toxico, porque para ellos no hay a donde reintentar.")


def main():
    demo_single_shard()
    demo_shuffle_sharding()
    demo_combinatorial_explosion()
    demo_retry_closes_the_loop()


if __name__ == "__main__":
    main()
