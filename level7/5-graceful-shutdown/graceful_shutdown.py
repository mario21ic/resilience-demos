"""Graceful shutdown / connection draining: cuando una instancia tiene
que dejar de existir (un deploy, un scale-down, mantenimiento de un
nodo), matarla de golpe (SIGKILL) corta cualquier request en curso a
mitad de camino. La secuencia correcta es:

  1. El orquestador manda SIGTERM (o corre un hook `preStop`, en
     Kubernetes) — "por favor, terminá lo que estás haciendo".
  2. La instancia deja de aceptar trafico NUEVO, pero sigue
     procesando lo que ya tenia en curso.
  3. Recien cuando termina (o se agota un periodo de gracia), el
     proceso sale solo — o el orquestador manda SIGKILL si se tomo
     demasiado tiempo.

Hay una carrera adicional, no obvia: aunque la instancia deje de
aceptar conexiones EN EL MISMO INSTANTE en que recibe la señal, el
load balancer puede tardar un rato en enterarse de que esta
apagandose y seguir mandandole trafico nuevo durante esa ventana. El
hook `preStop` de Kubernetes suele usarse justamente para dormir unos
segundos ANTES de empezar a rechazar conexiones, dandole tiempo al
balanceador a que se entere primero.
"""
import random


def draw_request_duration(rng: random.Random) -> float:
    """La mayoria de los requests en curso son cortos; una minoria son
    largos (una consulta pesada, un upload grande)."""
    if rng.random() < 0.1:
        return rng.uniform(20.0, 60.0)
    return rng.uniform(0.1, 5.0)


def simulate_abrupt_kill(in_flight_durations: list):
    """SIGKILL inmediato: TODOS los requests en curso se pierden, sin
    importar cuanto les faltaba para terminar."""
    return 0, len(in_flight_durations)


def simulate_graceful_shutdown(in_flight_durations: list, grace_period: float):
    """Se deja de aceptar trafico nuevo, pero los requests en curso
    tienen hasta `grace_period` para terminar solos. Los que exceden
    ese tiempo se cortan de todas formas (el orquestador no puede
    esperar para siempre)."""
    completed = sum(1 for d in in_flight_durations if d <= grace_period)
    dropped = len(in_flight_durations) - completed
    return completed, dropped


def simulate_deregistration_race(rng: random.Random, n_requests: int, lb_propagation_delay: float, prestop_sleep: float, arrival_window: float):
    """Simula requests NUEVOS llegando justo durante el apagado. El load
    balancer tarda `lb_propagation_delay` segundos en enterarse de que
    la instancia se esta yendo y dejar de mandarle trafico.

    Sin `preStop`, la app deja de aceptar conexiones en el instante
    t=0 (cuando recibe la señal) — cualquier request que el LB todavia
    le mande durante la ventana de propagacion falla (conexion
    rechazada). Con un `preStop` de `prestop_sleep` segundos, la app
    sigue aceptando conexiones durante ese tiempo, cubriendo la
    ventana de propagacion del LB.

    Devuelve (fallidos_sin_prestop, fallidos_con_prestop).
    """
    failed_without_prestop = 0
    failed_with_prestop = 0

    for _ in range(n_requests):
        arrival_time = rng.uniform(0, arrival_window)
        if arrival_time < lb_propagation_delay:
            failed_without_prestop += 1
            if arrival_time >= prestop_sleep:
                failed_with_prestop += 1

    return failed_without_prestop, failed_with_prestop
