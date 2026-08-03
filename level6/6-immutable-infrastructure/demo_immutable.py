"""Demo: Infraestructura inmutable.

20 servidores empiezan exactamente iguales. Con el tiempo, hacen falta
25 cambios (parches, hotfixes, ajustes).

  Mutable: cada cambio se aplica a mano, a un subconjunto de
           servidores (el que hacia falta en su momento) — nunca a
           todos de una, nunca documentado de forma centralizada.
  Inmutable: cada cambio se empaqueta en una imagen nueva, y TODOS los
             servidores se reemplazan por instancias de esa imagen.
"""
import random

from immutable import simulate_immutable_replacement, simulate_mutable_drift

N_SERVERS = 20
N_EVENTS = 25


def main():
    print(f"{N_SERVERS} servidores, originalmente identicos. {N_EVENTS} cambios con el tiempo.\n")

    rng = random.Random(3)
    n_unique_mutable, servers_mutable = simulate_mutable_drift(N_SERVERS, N_EVENTS, rng)

    n_unique_immutable, servers_immutable = simulate_immutable_replacement(N_SERVERS, N_EVENTS)

    print("=" * 70)
    print("MUTABLE: cada cambio se aplica a mano a un subconjunto de servidores")
    print("=" * 70)
    print(f"  configuraciones UNICAS entre los {N_SERVERS} servidores: {n_unique_mutable}")
    print(f"  ejemplos de configuraciones distintas encontradas:")
    seen = set()
    shown = 0
    for s in servers_mutable:
        key = tuple(sorted(s.items()))
        if key not in seen:
            seen.add(key)
            print(f"    {dict(s)}")
            shown += 1
        if shown >= 4:
            break
    print(f"\n  {n_unique_mutable}/{N_SERVERS} servidores 'identicos' en el papel terminaron siendo")
    print("  todos distintos entre si — nadie puede decir con certeza que cambios")
    print("  tiene CADA UNO sin entrar a revisarlo a mano.\n")

    print("=" * 70)
    print("INMUTABLE: cada cambio reemplaza TODOS los servidores por una imagen nueva")
    print("=" * 70)
    print(f"  versiones de imagen UNICAS entre los {N_SERVERS} servidores: {n_unique_immutable}")
    print(f"  todos los servidores corren la version: {servers_immutable[0]}")
    print("\n  no importa cuantos releases hayan pasado: en cualquier momento, TODOS")
    print("  los servidores son, byte a byte, la misma imagen — cero servidores")
    print("  'copo de nieve', cero incertidumbre sobre que esta corriendo donde.")


if __name__ == "__main__":
    main()
