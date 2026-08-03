"""Demo: Anti-entropy, read repair, Merkle trees.

  Parte 1 — Read repair: una lectura que toca varias replicas detecta
            que una esta atrasada y la repara al pasar, sin necesitar
            un proceso aparte para ese dato puntual.
  Parte 2 — Merkle trees: read repair solo arregla lo que se LEE. Para
            reparar datos "frios" (que casi nadie lee) hace falta un
            proceso de anti-entropy que compare replicas completas —
            y comparar millones de claves una por una no escala. Los
            arboles de Merkle permiten encontrar las pocas claves que
            realmente divergen sin leer casi nada del resto.
"""
import random

from merkle import build_merkle_tree, find_diverging_buckets, make_buckets
from replicas import Replica, quorum_read_with_repair


def demo_read_repair():
    print("=" * 70)
    print("Parte 1: read repair — reparar al pasar durante una lectura")
    print("=" * 70)

    a, b, c = Replica("A"), Replica("B"), Replica("C")
    a.put("user:42:email", "nuevo@mail.com", version=2)
    b.put("user:42:email", "nuevo@mail.com", version=2)
    c.put("user:42:email", "viejo@mail.com", version=1)  # C se perdio el ultimo write

    print("  antes de la lectura:")
    for r in (a, b, c):
        print(f"    {r.name}: {r.get('user:42:email')}")

    value, repaired = quorum_read_with_repair([a, b, c], "user:42:email")

    print(f"\n  valor devuelto al cliente: {value!r}")
    print(f"  replicas reparadas como efecto secundario de la lectura: {repaired}")
    print(f"  C despues del repair: {c.get('user:42:email')}")
    print("\n  el cliente nunca supo que hubo una divergencia — la recibio corregida,")
    print("  y C quedo al dia sin que nadie tuviera que notarlo por separado.\n")


def demo_merkle_efficiency():
    print("=" * 70)
    print("Parte 2: Merkle trees — encontrar 5 claves divergentes entre 1.000.000")
    print("=" * 70)

    n_keys = 1_000_000
    n_buckets = 1024
    keys = [f"key-{i:07d}" for i in range(n_keys)]

    replica_a = {k: "v1" for k in keys}
    replica_b = dict(replica_a)

    rng = random.Random(1)
    diverging_keys = set(rng.sample(keys, 5))
    for k in diverging_keys:
        replica_b[k] = "v2-stale"

    print(f"Dos replicas de {n_keys:,} claves cada una, con solo 5 realmente divergentes.\n")

    buckets_a = make_buckets(keys, replica_a, n_buckets)
    buckets_b = make_buckets(keys, replica_b, n_buckets)
    tree_a = build_merkle_tree(buckets_a)
    tree_b = build_merkle_tree(buckets_b)

    candidate_buckets, hash_comparisons = find_diverging_buckets(tree_a, tree_b)

    found_diffs = []
    key_comparisons = 0
    for bidx in candidate_buckets:
        for (ka, va), (kb, vb) in zip(buckets_a[bidx], buckets_b[bidx]):
            key_comparisons += 1
            if va != vb:
                found_diffs.append(ka)

    total_merkle_work = hash_comparisons + key_comparisons

    print(f"  comparacion de hashes en el arbol: {hash_comparisons}")
    print(f"  buckets candidatos a revisar clave por clave: {len(candidate_buckets)}/{n_buckets}")
    print(f"  comparaciones de claves individuales dentro de esos buckets: {key_comparisons}")
    print(f"  claves divergentes encontradas: {len(found_diffs)} (coincide con las {len(diverging_keys)} reales)")
    print(f"\n  trabajo total con Merkle: {total_merkle_work:,} comparaciones")
    print(f"  trabajo de un escaneo lineal completo: {n_keys:,} comparaciones")
    print(f"  -> {n_keys / total_merkle_work:.0f}x menos trabajo para encontrar exactamente las mismas 5 claves.")


def main():
    demo_read_repair()
    demo_merkle_efficiency()


if __name__ == "__main__":
    main()
