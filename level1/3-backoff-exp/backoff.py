"""Backoff exponencial: sin tope, con tope de delay (capped) y con tope
de exponente (truncated).

Este modulo NO trata sobre jitter (eso se ve en 4-jitter) — aca el
foco es unicamente en como evitar que el crecimiento exponencial se
vaya de control, que es un problema previo e independiente de si se
le agrega aleatoriedad o no.

Todas las variantes parten de la misma formula base:

    raw_delay(attempt) = base * factor ** (attempt - 1)
"""


def uncapped(attempt: int, base: float = 0.1, factor: float = 2.0) -> float:
    """Backoff exponencial puro, SIN ningun limite.

    Crece sin control: en pocos intentos el delay pasa de segundos a
    horas. Se incluye solo para mostrar el problema, nunca deberia
    usarse tal cual en produccion.
    """
    return base * (factor ** (attempt - 1))


def capped(
    attempt: int,
    base: float = 0.1,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> float:
    """"Capped exponential backoff": se limita el DELAY resultante.

    El exponente sigue creciendo con cada intento, pero el valor final
    se recorta a `max_delay`. Es la variante mas comun en la practica
    (SDKs de AWS, clientes HTTP, gRPC, etc.): simple de razonar, un
    solo parametro controla el peor caso.
    """
    return min(max_delay, uncapped(attempt, base, factor))


def truncated(
    attempt: int,
    base: float = 0.1,
    factor: float = 2.0,
    max_growth_attempts: int = 5,
    max_delay: float = 60.0,
) -> float:
    """"Truncated (binary) exponential backoff": se limita el EXPONENTE.

    Termino clasico del algoritmo CSMA/CD de Ethernet (IEEE 802.3): a
    partir de `max_growth_attempts` el exponente deja de crecer, asi
    que el delay se estabiliza en ese valor en vez de seguir subiendo
    en cada intento posterior. `max_delay` queda como red de
    seguridad adicional, casi nunca es el limite que efectivamente
    actua.

    La diferencia con `capped` es sutil pero importante: el "techo" de
    `truncated` sale de la propia formula exponencial evaluada en
    `max_growth_attempts` (un valor mas chico y predecible, tipico de
    querer muchos reintentos rapidos y acotados), mientras que el
    techo de `capped` es un valor de politica elegido a mano,
    independiente de cuantos intentos ya crecieron.
    """
    effective_attempt = min(attempt, max_growth_attempts)
    return min(max_delay, uncapped(effective_attempt, base, factor))
