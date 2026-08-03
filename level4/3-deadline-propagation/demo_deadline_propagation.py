"""Demo: Deadline propagation.

Un cliente esta dispuesto a esperar un total de 100ms. Su request pasa
por 3 capas intermedias antes de llegar a un salto final (una consulta
a una base de datos, por ejemplo), que a veces es lento.

  Sin propagacion: cada capa aplica un timeout LOCAL fijo (80ms) para
                   su proxima llamada, sin saber cuanto le queda
                   realmente al cliente original.
  Con propagacion: cada capa calcula el presupuesto REAL restante y lo
                    pasa hacia adelante; si ya no alcanza ni para que
                    la llamada final tenga sentido, se responde de
                    inmediato en vez de intentarla.
"""
import random

from deadlines import (
    MIN_USEFUL_TIME,
    ORIGINAL_DEADLINE,
    call_chain_with_propagation,
    call_chain_without_propagation,
)

SEED = 9
N_TRIALS = 50_000


def run(simulate_fn, seed):
    rng = random.Random(seed)
    totals, exceeded, attempted = [], 0, 0
    for _ in range(N_TRIALS):
        total, over_deadline, was_attempted = simulate_fn(rng)
        totals.append(total)
        exceeded += over_deadline
        attempted += was_attempted
    return totals, exceeded, attempted


def main():
    print(f"Deadline del cliente: {ORIGINAL_DEADLINE:.0f}ms. La cadena tiene 3 capas")
    print(f"intermedias antes de un salto final que a veces es lento.\n")

    totals_wo, exceeded_wo, attempted_wo = run(call_chain_without_propagation, SEED)
    totals_w, exceeded_w, attempted_w = run(call_chain_with_propagation, SEED)

    header = f"{'estrategia':>20} | {'latencia promedio':>18} | {'excede el deadline':>19} | {'llamada final intentada':>24}"
    print(header)
    print("-" * len(header))
    print(
        f"{'sin propagacion':>20} | {sum(totals_wo) / N_TRIALS:>16.1f}ms | "
        f"{exceeded_wo / N_TRIALS:>18.1%} | {attempted_wo / N_TRIALS:>23.1%}"
    )
    print(
        f"{'con propagacion':>20} | {sum(totals_w) / N_TRIALS:>16.1f}ms | "
        f"{exceeded_w / N_TRIALS:>18.1%} | {attempted_w / N_TRIALS:>23.1%}"
    )

    print(f"\nSin propagacion, el {exceeded_wo / N_TRIALS:.1%} de los requests termina tardando")
    print(f"MAS de los {ORIGINAL_DEADLINE:.0f}ms que el cliente estaba dispuesto a esperar — cada")
    print("capa 'cumplio' su propio timeout local, pero la suma se paso igual.")
    print(f"\nCon propagacion, el deadline original NUNCA se excede (0.0% por construccion):")
    print(f"cuando a una capa le quedan menos de {MIN_USEFUL_TIME:.0f}ms de presupuesto, ni")
    print(f"siquiera intenta la llamada final ({attempted_w / N_TRIALS:.1%} de las veces la salta")
    print("por completo) — responde con un fallback de inmediato en vez de arrancar")
    print("un trabajo que sabe que no va a poder terminar a tiempo.")


if __name__ == "__main__":
    main()
