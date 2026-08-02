"""Estrategias de backoff exponencial.

Estas funciones calculan CUANTO esperar antes del siguiente intento;
no hacen ninguna llamada de red (eso se ve en 2-retry). El objetivo
de este modulo es aislar el algoritmo de backoff para poder comparar
variantes lado a lado.

Referencia: "Exponential Backoff and Jitter" (AWS Architecture Blog),
que define full jitter, equal jitter y decorrelated jitter como
mejoras sobre el backoff exponencial puro.
"""
import random


def exponential_delay(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """Backoff exponencial puro, sin aleatoriedad: base * factor^(attempt-1).

    `attempt` empieza en 1. El resultado se acota a `max_delay` para
    que el crecimiento exponencial no termine esperando minutos u
    horas tras unos pocos intentos.
    """
    return min(max_delay, base * (factor ** (attempt - 1)))


def full_jitter(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """AWS "full jitter": un valor uniforme entre 0 y el tope exponencial.

    Maximiza la dispersion entre clientes (evita que todos reintenten
    en el mismo instante) a costa de que algunos reintenten casi de
    inmediato.
    """
    cap = exponential_delay(attempt, base, factor, max_delay)
    return random.uniform(0, cap)


def equal_jitter(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """AWS "equal jitter": mitad fija + mitad aleatoria del tope exponencial.

    Dispersa menos que full jitter, pero garantiza una espera minima
    (util si se quiere evitar reintentos casi inmediatos).
    """
    cap = exponential_delay(attempt, base, factor, max_delay)
    return cap / 2 + random.uniform(0, cap / 2)


def decorrelated_jitter(
    prev_delay: float,
    base: float = 0.5,
    max_delay: float = 30.0,
) -> float:
    """AWS "decorrelated jitter": uniforme entre `base` y `prev_delay * 3`.

    No depende del numero de intento sino de la espera anterior, lo
    que en la practica da una dispersion aun mayor que full jitter
    manteniendo una tendencia creciente.
    """
    return min(max_delay, random.uniform(base, prev_delay * 3))
