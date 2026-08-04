"""Demo: Leader election con fencing tokens.

  Parte 1 — Eleccion normal: un candidato adquiere el lock y lo
            renueva antes de que expire, manteniendo el liderazgo
            indefinidamente.
  Parte 2 — El escenario de Kleppmann: el lider entra en una pausa
            larga (GC, VM stall) que supera su lease. Otro candidato
            toma el liderazgo mientras tanto. Cuando el primero se
            despierta, sigue creyendose el lider e intenta escribir —
            el fencing token es lo unico que evita que lo logre.
"""
from leader_election import FencedError, FencedStorage, LeaseLock

TTL = 10.0


def demo_normal_election_and_renewal():
    print("=" * 70)
    print("Parte 1: eleccion normal, con renovacion a tiempo")
    print("=" * 70)

    lock = LeaseLock(ttl=TTL)
    token = lock.try_acquire("A", now=0)
    print(f"  t=0: A adquiere el lock (fencing token={token})")

    for now in (8, 16, 24):
        renewed = lock.renew("A", now)
        print(f"  t={now}: A renueva antes de que expire -> {'OK' if renewed else 'FALLO'}")

    print("  A sigue siendo lider indefinidamente, mientras siga renovando a tiempo.\n")


def demo_gc_pause_scenario():
    print("=" * 70)
    print("Parte 2: el escenario de Kleppmann — un lider zombie con lease vencido")
    print("=" * 70)

    lock = LeaseLock(ttl=TTL)
    token_a = lock.try_acquire("A", now=0)
    print(f"  t=0:  A adquiere el lock (fencing token={token_a})")

    print("  t=1:  A entra en una pausa larga (GC de 25s) — no puede renovar")

    token_b = lock.try_acquire("B", now=15)
    print(f"  t=15: el lease de A ya vencio (TTL={TTL:.0f}s); B adquiere el lock "
          f"(fencing token={token_b})")

    storage = FencedStorage()
    storage.advance_generation(token_b)
    print(f"  el storage compartido ya conoce la generacion {token_b}")

    print(f"\n  t=26: A se despierta de la pausa. NO SABE que paso el tiempo — sigue")
    print(f"        creyendose el lider, e intenta escribir con su token viejo ({token_a})")
    try:
        storage.write(token_a, "config", "cambio de A (invalido)")
        print("    -> aceptado (esto NO deberia pasar)")
    except FencedError as exc:
        print(f"    -> RECHAZADO: {exc}")

    print(f"\n  B, el lider real, escribe con su token ({token_b}):")
    storage.write(token_b, "config", "cambio de B (el lider vigente)")
    print(f"    -> aceptado. valor final: {storage.read('config')!r}")

    print("\n  A nunca se cayo — solo estuvo pausado mas tiempo del que duraba su lease.")
    print("  Sin el fencing token, su escritura tardia se hubiera aplicado igual,")
    print("  pisando silenciosamente el cambio del lider real.")


def main():
    demo_normal_election_and_renewal()
    demo_gc_pause_scenario()


if __name__ == "__main__":
    main()
