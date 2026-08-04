"""Demo: Consenso (Raft, Paxos) — quorum como base de la resiliencia.

  Parte 1 — Eleccion de lider: por que dos candidatos NUNCA pueden
            ganar la mayoria en la misma ronda, y que pasa cuando el
            voto se fragmenta entre varios candidatos (nadie gana,
            hace falta una nueva ronda).
  Parte 2 — Confirmar una entrada del log: una entrada replicada a
            una mayoria de nodos es segura para siempre, sin importar
            que nodos fallen despues; una que no llego a mayoria
            puede perderse.
"""
from consensus import is_safe_from_future_majorities, majority, run_election

N_NODES = 5


def demo_leader_election():
    print("=" * 70)
    print("Parte 1: eleccion de lider — por que solo puede ganar UNO")
    print("=" * 70)

    maj = majority(N_NODES)
    print(f"{N_NODES} nodos, mayoria = {maj}.\n")

    winners, _ = run_election(N_NODES, {"A": 3, "B": 2})
    print(f"  votos A=3, B=2 -> gana: {winners}")

    winners, _ = run_election(N_NODES, {"A": 2, "B": 2, "C": 1})
    print(f"  votos A=2, B=2, C=1 (voto fragmentado) -> gana: {winners or 'nadie'} "
          f"(hace falta otra ronda)")

    print(f"\n  ¿pueden dos candidatos ganar la mayoria en la MISMA ronda? Si A y B")
    print(f"  consiguieran {maj} votos cada uno, sumarian {maj * 2} votos — pero solo hay")
    print(f"  {N_NODES} nodos votando en total. Es matematicamente imposible.\n")


def demo_commit_safety():
    print("=" * 70)
    print("Parte 2: una entrada comprometida (en mayoria) nunca se pierde")
    print("=" * 70)

    committed = {0, 1, 2}  # el lider replico esta entrada a una mayoria antes de confirmarla
    uncommitted = {0, 1}   # esta otra solo llego a 2 de 5 nodos: todavia NO es mayoria

    print(f"  entrada A, replicada a los nodos {committed} (mayoria: {majority(N_NODES)}):")
    print(f"    ¿esta a salvo de cualquier eleccion futura? "
          f"{is_safe_from_future_majorities(N_NODES, committed)}")

    print(f"\n  entrada B, replicada solo a los nodos {uncommitted} (todavia no es mayoria):")
    print(f"    ¿esta a salvo de cualquier eleccion futura? "
          f"{is_safe_from_future_majorities(N_NODES, uncommitted)}")

    print("\n  si el lider se cae justo despues de replicar la entrada B a solo 2 nodos,")
    print("  una eleccion futura podria formarse enteramente con los otros 3 nodos —")
    print("  que nunca vieron la entrada B. Esa entrada se pierde para siempre, como si")
    print("  nunca hubiera pasado. Por eso Raft y Paxos NUNCA confirman un cambio al")
    print("  cliente hasta que una mayoria real lo tiene replicado.")


def main():
    demo_leader_election()
    demo_commit_safety()


if __name__ == "__main__":
    main()
