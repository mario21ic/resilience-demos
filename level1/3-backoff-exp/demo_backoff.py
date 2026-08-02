"""Demo del patron de resiliencia: Backoff exponencial con topes.

El backoff exponencial puro (`base * factor ** (attempt - 1)`) crece
sin limite: en pocos intentos pasa de milisegundos a horas. Este demo
compara tres formas de evitar eso (sin agregar jitter, que se ve por
separado en 4-jitter):

  1) uncapped   - sin ningun tope (el problema).
  2) capped     - se recorta el DELAY resultante a un maximo fijo.
  3) truncated  - se recorta el EXPONENTE despues de N intentos, asi
                  el delay se estabiliza en un valor mas chico y
                  predecible que sale de la propia formula.

Ademas muestra por que capar el delay POR INTENTO no alcanza si el
llamador tiene un presupuesto de tiempo total (deadline): hay que
capar tambien el tiempo acumulado de reintento, no solo cada espera
individual.
"""
from backoff import capped, truncated, uncapped

BASE = 0.1
FACTOR = 2.0
MAX_ATTEMPTS_TABLE = 20

CAPPED_MAX_DELAY = 30.0
TRUNCATED_MAX_GROWTH = 5
TRUNCATED_MAX_DELAY = 60.0


def format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def print_growth_table():
    print("Crecimiento del delay por intento\n")
    print(f"{'intento':>7} | {'uncapped':>12} | {'capped (max=30s)':>17} | {'truncated (N=5, max=60s)':>25}")
    print("-" * 70)
    for attempt in range(1, MAX_ATTEMPTS_TABLE + 1):
        raw = uncapped(attempt, BASE, FACTOR)
        cap = capped(attempt, BASE, FACTOR, CAPPED_MAX_DELAY)
        trunc = truncated(attempt, BASE, FACTOR, TRUNCATED_MAX_GROWTH, TRUNCATED_MAX_DELAY)
        print(
            f"{attempt:>7} | {format_seconds(raw):>12} | {format_seconds(cap):>17} | {format_seconds(trunc):>25}"
        )
    print()
    print("uncapped pasa de decimas de segundo a horas en menos de 20 intentos.")
    print("capped se estabiliza en el techo de politica (30s) que elegimos a mano.")
    print("truncated se estabiliza antes (en el intento 5) y en un valor mas bajo")
    print("(1.6s) que sale de la formula, no de un numero elegido arbitrariamente.")
    print("El 'max=60s' de truncated ni siquiera llega a activarse: es solo la red")
    print("de seguridad para un factor/base distinto que si pudiera superarlo.\n")


# --- Backoff por intento no alcanza si hay un presupuesto de tiempo total --


def run_retry_loop_with_deadline(delay_fn, deadline_s: float, max_attempts: int = 20):
    """Simula intentos fallidos consecutivos, respetando un presupuesto
    total de tiempo ademas del propio calculo de backoff.

    Se detiene si el PROXIMO delay haria superar el presupuesto total,
    incluso si `max_attempts` todavia no se alcanzo: capar cada espera
    individual no evita que la SUMA de esperas exceda un deadline.
    """
    elapsed = 0.0
    for attempt in range(1, max_attempts + 1):
        delay = delay_fn(attempt)
        if elapsed + delay > deadline_s:
            print(
                f"  intento {attempt}: el siguiente delay ({delay:.2f}s) superaria el "
                f"presupuesto ({deadline_s:.0f}s) con {elapsed:.2f}s ya consumidos -> se aborta"
            )
            return attempt - 1, elapsed
        elapsed += delay
        print(f"  intento {attempt}: espera {delay:.2f}s (acumulado {elapsed:.2f}s)")
    print(f"  se alcanzo max_attempts={max_attempts} sin agotar el presupuesto")
    return max_attempts, elapsed


def compare_deadline_budget():
    deadline = 20.0
    print(f"Presupuesto de tiempo total del llamador: {deadline:.0f}s\n")

    print("Con 'capped' (max_delay=30s) — cada espera individual es 'legal',")
    print("pero igual se puede agotar el presupuesto antes de max_attempts:")
    attempts_done, elapsed = run_retry_loop_with_deadline(
        lambda a: capped(a, BASE, FACTOR, CAPPED_MAX_DELAY), deadline
    )
    print(f"  -> {attempts_done} intentos completados, {elapsed:.2f}s consumidos\n")

    print("Con 'truncated' (N=5, max_delay=60s) — el plateau mas bajo permite")
    print("mas intentos dentro del mismo presupuesto:")
    attempts_done, elapsed = run_retry_loop_with_deadline(
        lambda a: truncated(a, BASE, FACTOR, TRUNCATED_MAX_GROWTH, TRUNCATED_MAX_DELAY), deadline
    )
    print(f"  -> {attempts_done} intentos completados, {elapsed:.2f}s consumidos\n")

    print("Capar el delay por intento y capar el tiempo total del llamador son")
    print("mecanismos distintos y complementarios: el primero acota CADA espera,")
    print("el segundo acota CUANTO tiempo total se le puede dedicar a reintentar.")


def main():
    print_growth_table()
    compare_deadline_budget()


if __name__ == "__main__":
    main()
