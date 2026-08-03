"""Tied requests: la variante de hedging (ver
[1-hedged-requests](../1-hedged-requests)) donde, en vez de esperar un
umbral antes de disparar una copia, se manda el request a DOS replicas
SIMULTANEAMENTE desde el inicio ("atadas" entre si) y se cancela a la
perdedora en cuanto la ganadora empieza a responder.

La diferencia importa cuando la latencia de cola viene de la COLA de
trabajo pendiente en cada replica, no de que la ejecucion en si sea
lenta: hedging solo reacciona despues de un umbral calibrado (tipico:
al tiempo de EJECUCION esperado), pero un umbral asi no tiene en
cuenta cuanto trabajo de OTROS requests ya esta encolado en cada
replica en este preciso instante. Tied requests no necesita adivinar
nada: manda a ambas de una, y gana la que este menos ocupada ahora
mismo.

El costo: tied requests solo vale la pena si existe un mecanismo de
cancelacion RAPIDO entre replicas — sin eso, cada request atado cuesta
el doble de trabajo real, siempre.
"""
import random


def draw_background_load(rng: random.Random) -> float:
    """Cuanto trabajo de OTROS requests ya esta encolado en una
    replica en este instante. La mayoria de las veces es poco (carga
    liviana); ocasionalmente una replica tiene un "hot spot" (una
    rafaga de trafico, un vecino ruidoso) con mucho mas encolado.
    """
    if rng.random() < 0.1:
        return rng.uniform(50.0, 150.0)
    return rng.uniform(0.0, 10.0)


def simulate_wasted_work(rng: random.Random, exec_time: float, cancel_latency: float, n_trials: int):
    """Compara cuanto trabajo de EJECUCION se desperdicia en la
    replica perdedora, con y sin cancelacion rapida.

    Sin cancelacion, la perdedora siempre corre el request completo
    (el resultado se descarta, pero el trabajo ya se hizo). Con
    cancelacion rapida, la señal de "ya gano la otra" le llega a la
    perdedora `cancel_latency` despues de que la ganadora termino — si
    todavia no habia arrancado a ejecutar (seguia en su propia cola),
    el desperdicio es cero.
    """
    naive_wasted_total = 0.0
    fast_wasted_total = 0.0

    for _ in range(n_trials):
        bg_a = draw_background_load(rng)
        bg_b = draw_background_load(rng)
        winner_bg, loser_bg = min(bg_a, bg_b), max(bg_a, bg_b)
        winner_finish = winner_bg + exec_time

        naive_wasted_total += exec_time  # la perdedora SIEMPRE corre completo

        cancel_arrives_at = winner_finish + cancel_latency
        loser_exec_start = loser_bg
        loser_exec_end = loser_bg + exec_time

        if cancel_arrives_at <= loser_exec_start:
            wasted = 0.0
        elif cancel_arrives_at >= loser_exec_end:
            wasted = exec_time
        else:
            wasted = cancel_arrives_at - loser_exec_start
        fast_wasted_total += wasted

    return naive_wasted_total / n_trials, fast_wasted_total / n_trials


def simulate_latency_comparison(rng: random.Random, n_trials: int, exec_time: float, hedge_delay: float):
    """Compara la latencia observada bajo cuatro estrategias:

      - solo_a: siempre a la misma replica preferida, sin backup.
      - hedged: a A primero; si no termino para `hedge_delay`, tambien
        a B (que puede tener SU PROPIA cola pendiente en ese momento).
      - tied: a ambas desde el inicio, se toma la que termine primero
        (asume cancelacion rapida, ver `simulate_wasted_work`).
      - ideal: un oraculo que siempre elige la replica correcta de
        entrada — el techo teorico que tied intenta alcanzar.
    """
    only_a, hedged, tied, ideal = [], [], [], []

    for _ in range(n_trials):
        bg_a = draw_background_load(rng)
        bg_b = draw_background_load(rng)
        finish_a = bg_a + exec_time
        finish_b = bg_b + exec_time

        only_a.append(finish_a)
        ideal.append(min(finish_a, finish_b))
        tied.append(min(finish_a, finish_b))

        if finish_a <= hedge_delay:
            hedged.append(finish_a)
        else:
            hedge_b_finish = hedge_delay + max(0.0, bg_b - hedge_delay) + exec_time
            hedged.append(min(finish_a, hedge_b_finish))

    return only_a, hedged, tied, ideal


def percentile(sorted_values: list, p: float) -> float:
    idx = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return sorted_values[idx]
