"""Tres variantes de jitter para backoff exponencial.

Referencia: "Exponential Backoff and Jitter" (AWS Architecture Blog).
`cap` es el techo determinista del backoff exponencial puro para el
intento actual (ver 3-backoff-exp): no depende de aleatoriedad, solo
del numero de intento.

    cap(attempt) = min(max_delay, base * factor ** (attempt - 1))

Cada variante decide COMO usar ese techo para elegir la espera real.
"""
import random


def exponential_cap(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    return min(max_delay, base * (factor ** (attempt - 1)))


def full_jitter(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """uniform(0, cap). Maxima dispersion posible entre clientes.

    Contra: algunos clientes reintentan casi de inmediato (delay ~ 0),
    lo que puede no darle nada de respiro al servicio en esos casos
    particulares, aunque en promedio disperse mejor que las otras dos.
    """
    cap = exponential_cap(attempt, base, factor, max_delay)
    return random.uniform(0, cap)


def equal_jitter(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """cap/2 + uniform(0, cap/2). Garantiza una espera minima de cap/2.

    Dispersa menos que full jitter (el rango util es la mitad), pero
    evita el caso "reintento casi inmediato" que si permite full jitter.
    """
    cap = exponential_cap(attempt, base, factor, max_delay)
    return cap / 2 + random.uniform(0, cap / 2)


def decorrelated_jitter(
    prev_delay: float,
    base: float = 0.5,
    max_delay: float = 30.0,
) -> float:
    """uniform(base, prev_delay * 3), acotado a max_delay.

    No depende del numero de intento sino de la ULTIMA espera usada,
    por eso "decorrelacionado": la formula en si es la misma en todos
    los intentos. En la practica es la que mas dispersa (en el
    benchmark del post de AWS es la que menos llamadas totales y menor
    tiempo total de recuperacion produce).
    """
    return min(max_delay, random.uniform(base, prev_delay * 3))
