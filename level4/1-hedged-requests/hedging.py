"""Hedged requests, del paper "The Tail at Scale" (Dean & Barroso,
2013): si una llamada no respondio dentro de un umbral, se dispara una
copia ("hedge") a otra replica, y se toma la que responda primero. La
otra se descarta.

La motivacion es la latencia de cola: en un servicio con muchas
replicas, la latencia de un request individual tiene una cola larga
(GC pauses, contencion de disco, ruido del vecino) aunque el promedio
sea excelente. Si un cliente necesita agregar resultados de cientos de
replicas para responder UN request (el caso tipico de busqueda,
recomendaciones, etc.), la latencia final la define la mas LENTA de
todas — y con suficientes replicas, "al menos una tarda" se vuelve
casi seguro.

`draw_latency` simula una replica cuya latencia normalmente es rapida,
pero con una probabilidad `P_SLOW` cae en un modo mucho mas lento (un
stall real: GC, IO, throttling) — ese modo lento es lo que dispara la
cola larga en p99/p999.
"""
import random

P_SLOW = 0.05
FAST_MEAN, FAST_STD = 10.0, 2.0      # milisegundos, caso comun
SLOW_MIN, SLOW_MAX = 100.0, 300.0    # milisegundos, el "stall" ocasional


def draw_latency(rng: random.Random) -> float:
    if rng.random() < P_SLOW:
        return rng.uniform(SLOW_MIN, SLOW_MAX)
    return max(0.5, rng.gauss(FAST_MEAN, FAST_STD))


def percentile(sorted_values: list, p: float) -> float:
    idx = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return sorted_values[idx]


def hedged_call(rng: random.Random, hedge_delay: float) -> tuple:
    """Simula un request con hedging: si la llamada primaria no
    hubiera respondido para `hedge_delay`, se dispara una segunda
    llamada a OTRA replica (una muestra independiente de la misma
    distribucion), y se toma lo que responda primero.

    Devuelve (latencia_observada, se_disparo_el_hedge).
    """
    primary = draw_latency(rng)
    if primary <= hedge_delay:
        return primary, False

    hedge = draw_latency(rng)
    finish_primary = primary
    finish_hedge = hedge_delay + hedge
    return min(finish_primary, finish_hedge), True
