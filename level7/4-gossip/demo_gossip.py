"""Demo: Gossip — difusion de membresia tolerante a particiones.

  Parte 1 — Propagacion epidemica: un cluster de 1000 nodos, sin fallas,
            informado en pocas rondas gracias al crecimiento exponencial.
  Parte 2 — Tolerancia a fallas: el 30% de los nodos esta caido — el
            gossip sigue convergiendo, casi al mismo ritmo, sobre los
            nodos que quedan vivos.
  Parte 3 — El contraste: un coordinador central que falla justo a el
            deja a TODOS sin enterarse — gossip no tiene ese punto
            unico de falla.
"""
import random

from gossip import simulate_centralized_broadcast, simulate_gossip

N_NODES = 1000


def demo_epidemic_spread():
    print("=" * 70)
    print("Parte 1: propagacion epidemica, sin fallas")
    print("=" * 70)

    rng = random.Random(1)
    history, n_alive = simulate_gossip(N_NODES, rng)

    print(f"{N_NODES} nodos. Progreso de nodos informados por ronda:")
    print(f"  {history[:8]}...")
    print(f"  rondas hasta informar a todos: {len(history) - 1}")
    print(f"\n  la cantidad de informados se aproximadamente DUPLICA en cada una de las")
    print("  primeras rondas — asi se cubre un cluster de 1000 nodos en apenas")
    print(f"  {len(history) - 1} rondas, no en 1000.\n")


def demo_partition_tolerance():
    print("=" * 70)
    print("Parte 2: tolerancia a fallas — 30% de los nodos caidos")
    print("=" * 70)

    rng_failures = random.Random(1)
    failed = frozenset(rng_failures.sample(range(N_NODES), 300))

    rng = random.Random(2)
    history, n_alive = simulate_gossip(N_NODES, rng, failed_nodes=failed)

    print(f"  nodos vivos: {n_alive}/{N_NODES} (300 caidos, al azar)")
    print(f"  rondas hasta informar a TODOS los nodos vivos: {len(history) - 1}")
    print(f"  progreso: {history}")
    print("\n  el gossip no depende de ningun nodo en particular para propagarse — hay")
    print("  tantos caminos posibles entre dos nodos cualquiera que perder un 30% del")
    print("  cluster casi no cambia cuantas rondas hacen falta para converger.\n")


def demo_centralized_contrast():
    print("=" * 70)
    print("Parte 3: el contraste — un coordinador central que falla")
    print("=" * 70)

    rng = random.Random(3)
    failed = frozenset(rng.sample(range(N_NODES), 300))
    coordinator = next(iter(failed))  # el coordinador, por mala suerte, es uno de los caidos

    informed = simulate_centralized_broadcast(N_NODES, coordinator, failed)
    print(f"  coordinador elegido: nodo {coordinator} (que resulta estar caido)")
    print(f"  nodos informados: {informed}/{N_NODES - len(failed)} vivos")
    print("\n  con un unico coordinador, su propia caida es un punto unico de falla")
    print("  para TODA la difusion — no hay ningun camino alternativo. El gossip no")
    print("  tiene esa fragilidad porque nunca depende de un solo nodo en particular.")


def main():
    demo_epidemic_spread()
    demo_partition_tolerance()
    demo_centralized_contrast()


if __name__ == "__main__":
    main()
