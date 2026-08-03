"""Los tres tipos de probe de salud (terminologia popularizada por
Kubernetes, pero el concepto es generico a cualquier orquestador o
load balancer con health checks) y la diferencia entre un chequeo
superficial y uno profundo.

  - liveness:  "esta vivo el proceso?" Si falla, el orquestador MATA
               y REINICIA la instancia. Tiene que ser barato y
               SUPERFICIAL: confirmar que el proceso responde (el
               event loop no esta trabado, no hay un deadlock), nunca
               revisar dependencias externas. Reiniciar el proceso no
               arregla una base de datos caida — solo agrega un
               reinicio de mas arriba de una falla que sigue ahi.

  - readiness: "esta lista esta instancia para recibir trafico AHORA?"
               Si falla, se la saca de la rotacion del load balancer
               — sin matarla ni reiniciarla. Aca si tiene sentido
               revisar dependencias, pero solo las REALMENTE
               esenciales para poder servir: si se incluye una
               dependencia no esencial, una falla parcial en algo
               secundario tumba el 100% del trafico por algo que ni
               siquiera hacia falta para atender la mayoria de los
               requests.

  - startup:   una version mas permisiva de liveness, usada solo
               mientras la instancia arranca (init lento, precarga de
               cache, JIT warmup), para no matarla por "no responde
               todavia" cuando en realidad solo esta iniciando. Una
               vez que pasa, liveness y readiness toman el control.

Este modulo no implementa clases: las funciones de
`demo_health_checks.py` simulan directamente, tick a tick, que
fraccion de la flota queda disponible bajo cada configuracion.
"""

def simulate_liveness_scope(db_healthy: list[bool], restart_time: int, deep_liveness: bool) -> list[float]:
    """Fraccion de capacidad disponible, tick a tick, segun donde se
    puso el chequeo de la base de datos.

    `deep_liveness=True` (mal diseño): la liveness revisa la DB. Si
    falla, la instancia se reinicia, y el reinicio no puede terminar
    de completarse (reconectar, precalentar cache, etc.) hasta que la
    DB este sana durante `restart_time` ticks seguidos — el reinicio
    se suma ENCIMA de la falla original.

    `deep_liveness=False` (buen diseño): la liveness es superficial y
    nunca falla por la DB. Solo la READINESS la revisa: la instancia
    se saca de rotacion mientras la DB esta caida, pero vuelve a
    estar lista en el primer check posterior a que la DB se recupere
    — sin reinicio de por medio.
    """
    fractions = []
    restart_remaining = 0

    for healthy in db_healthy:
        if deep_liveness:
            if not healthy:
                restart_remaining = restart_time  # cae y se queda reiniciando mientras la DB no vuelva
                fraction = 0.0
            elif restart_remaining > 0:
                restart_remaining -= 1
                fraction = 0.0
            else:
                fraction = 1.0
        else:
            fraction = 1.0 if healthy else 0.0

        fractions.append(fraction)

    return fractions


def simulate_readiness_scope(core_healthy: list[bool], optional_healthy: list[bool], checks_optional: bool) -> list[float]:
    """Fraccion de capacidad disponible, tick a tick, segun si la
    readiness revisa (mal diseño, `checks_optional=True`) tambien una
    dependencia NO esencial, ademas de la esencial (`core_healthy`).

    Si la readiness solo mira lo esencial, una falla en algo opcional
    no saca a la instancia de rotacion — esa funcionalidad puntual se
    degrada (via fallback, ver level1/8-fallback), pero el resto del
    trafico se sigue sirviendo con normalidad.
    """
    fractions = []
    for core_ok, optional_ok in zip(core_healthy, optional_healthy):
        if not core_ok:
            fractions.append(0.0)
        elif checks_optional and not optional_ok:
            fractions.append(0.0)
        else:
            fractions.append(1.0)
    return fractions
