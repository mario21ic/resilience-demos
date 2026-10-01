"""Chaos engineering: verificar con un experimento real si un
mecanismo de resiliencia (un circuit breaker, un failover, un retry)
realmente funciona como se supone, en vez de confiar en que funciona
porque asi se diseño.

El metodo cientifico aplicado a sistemas en produccion:

  1. Definir un ESTADO ESTABLE medible (ej. tasa de exito de los
     requests).
  2. Formular una HIPOTESIS: "el estado estable se mantiene incluso si
     inyectamos esta falla especifica".
  3. Diseñar un EXPERIMENTO con un radio de impacto ACOTADO — empezar
     chico (1% del trafico), nunca con el 100% de una.
  4. Observar si la hipotesis se sostiene o se refuta.
  5. Si se sostiene, aumentar gradualmente el alcance para ganar mas
     confianza. Si se refuta, se encontro una debilidad real — ANTES
     de que un incidente real la expusiera sin que nadie estuviera
     mirando ni preparado.
"""
import random


def simulate_experiment(n_requests: int, blast_radius: float, resilience_mechanism_works: bool, rng: random.Random) -> float:
    """Simula una rafaga de requests, de los cuales una fraccion
    `blast_radius` golpea contra la falla inyectada por el
    experimento. Si el mecanismo de resiliencia bajo prueba
    (`resilience_mechanism_works`) funciona de verdad, esos requests
    igual tienen exito (redirigidos, reintentados, lo que corresponda);
    si no, fallan.

    Devuelve la tasa de exito observada durante el experimento.
    """
    successes = 0
    for _ in range(n_requests):
        hits_injected_failure = rng.random() < blast_radius
        if hits_injected_failure:
            if resilience_mechanism_works:
                successes += 1
        else:
            successes += 1
    return successes / n_requests
