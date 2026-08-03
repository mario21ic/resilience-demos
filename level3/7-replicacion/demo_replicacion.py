"""Demo: Replicacion — sincrona, asincrona, por quorum; leader-follower
vs multi-leader.

  Parte 1 — Sincrona vs asincrona: la asincrona confirma mas rapido,
            pero puede perder writes YA CONFIRMADOS si el leader se
            cae antes de terminar de replicarlos. La sincrona nunca
            pierde un write confirmado, al costo de mayor latencia.
  Parte 2 — Quorum: con W+R>N, toda lectura esta matematicamente
            garantizada de tocar al menos una replica con el ultimo
            write. Con W+R<=N, no hay garantia — se cuantifica cuanto.
  Parte 3 — Leader-follower vs multi-leader: un leader unico define un
            orden real sin ambiguedad; con multiples leaders, resolver
            conflictos por "ultimo timestamp gana" (LWW) puede
            invertir el orden real si los relojes de las regiones no
            estan perfectamente sincronizados.
"""
import random

from replication import (
    LeaderFollowerCluster,
    MultiLeaderCluster,
    empirical_stale_read_rate,
    probability_no_overlap,
    simulate_writes,
)


# --- Parte 1: sincrona vs asincrona ------------------------------------------


def demo_sync_vs_async():
    print("=" * 70)
    print("Parte 1: replicacion sincrona vs asincrona")
    print("=" * 70)

    n_writes, write_interval, follower_latency, crash_at = 10, 0.02, 0.05, 0.15
    print(f"{n_writes} writes cada {write_interval * 1000:.0f}ms, la replicacion a followers")
    print(f"tarda {follower_latency * 1000:.0f}ms, y el leader se cae en t={crash_at * 1000:.0f}ms.\n")

    _, lost, never_acked = simulate_writes(n_writes, write_interval, follower_latency, crash_at, "async")
    print(f"ASINCRONA: writes {[e['id'] for e in lost]} fueron confirmados al cliente pero")
    print(f"  NUNCA llegaron a un follower antes del crash -> PERDIDOS en silencio.")
    print(f"  (los writes {[e['id'] for e in never_acked]} ni siquiera llegaron a confirmarse:")
    print(f"  el cliente hubiera visto un error, no una falsa confirmacion)\n")

    _, lost, never_acked = simulate_writes(n_writes, write_interval, follower_latency, crash_at, "sync")
    print(f"SINCRONA: writes perdidos = {[e['id'] for e in lost]} (siempre vacio: nunca se")
    print(f"  confirma un write que no llego a un follower).")
    print(f"  costo: los writes {[e['id'] for e in never_acked]} ni siquiera llegaron a")
    print(f"  confirmarse antes del crash (mas lenta, pero nunca miente).\n")


# --- Parte 2: quorum ----------------------------------------------------------


def demo_quorum():
    print("=" * 70)
    print("Parte 2: quorum — cuando W+R>N garantiza no leer datos viejos")
    print("=" * 70)
    print("5 replicas. Se compara la probabilidad de que una lectura no toque")
    print("NINGUNA replica con el ultimo write, para distintos tamanos de quorum.\n")

    rng = random.Random(1)
    header = f"{'W':>3} {'R':>3} {'W+R vs N':>10} | {'prob. teorica':>14} | {'medido (20000 pruebas)':>22}"
    print(header)
    print("-" * len(header))
    for w, r in ((3, 3), (2, 2), (1, 1)):
        relation = "> N (seguro)" if w + r > 5 else "<= N (riesgo)"
        theoretical = probability_no_overlap(5, w, r)
        empirical = empirical_stale_read_rate(5, w, r, 20000, rng)
        print(f"{w:>3} {r:>3} {relation:>10} | {theoretical:>13.1%} | {empirical:>21.1%}")

    print("\nCon W=3,R=3 (W+R=6>5) es matematicamente imposible elegir un quorum de")
    print("lectura que no toque ninguna de las 3 replicas que ya tienen el ultimo")
    print("write. Con W=1,R=1, el 80% de las lecturas puede devolver un valor viejo.\n")


# --- Parte 3: leader-follower vs multi-leader --------------------------------


def demo_leader_follower_vs_multi_leader():
    print("=" * 70)
    print("Parte 3: leader-follower vs multi-leader")
    print("=" * 70)

    print("Leader-follower: todos los writes pasan por un unico leader.")
    single = LeaderFollowerCluster()
    seq_a = single.write("precio_42", 100)
    seq_b = single.write("precio_42", 150)
    print(f"  write A (valor=100) recibe secuencia #{seq_a}")
    print(f"  write B (valor=150) recibe secuencia #{seq_b}")
    print(f"  valor final: {single.read('precio_42')} — orden definido por el leader, sin ambiguedad\n")

    print("Multi-leader: cada region acepta escrituras locales de inmediato.")
    print("EU escribe en tiempo real t=100.0 (su reloj esta sincronizado).")
    print("US escribe DESPUES, en tiempo real t=100.5 — pero el reloj de US esta")
    print("atrasado 1.5s, asi que su timestamp local queda en 99.0.\n")

    multi = MultiLeaderCluster(["eu", "us"])
    multi.write("eu", "precio_42", 150, local_timestamp=100.0)
    multi.write("us", "precio_42", 100, local_timestamp=99.0)

    winner, losers = multi.resolve("precio_42")
    print(f"  LWW por timestamp local elige como ganador a: {winner}")
    print(f"  se descarta silenciosamente: {losers}")
    print("\n  En el mundo real, US escribio DESPUES que EU (100.5 > 100.0) — deberia")
    print("  ganar. LWW eligio al reves, exactamente porque comparo relojes de dos")
    print("  regiones que no estaban perfectamente sincronizados entre si.")
    print("\n  Leader-follower no tiene este problema porque nunca compara relojes de")
    print("  distintas maquinas: el orden lo define quien llego primero al UNICO leader.")


def main():
    demo_sync_vs_async()
    demo_quorum()
    demo_leader_follower_vs_multi_leader()


if __name__ == "__main__":
    main()
