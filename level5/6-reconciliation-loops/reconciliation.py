"""Reconciliation loops: el modelo de control de Kubernetes. En vez de
ejecutar una accion una vez y confiar en que el resultado se mantenga,
un controlador compara continuamente el estado DESEADO contra el
estado REAL observado, y aplica la diferencia — una y otra vez, para
siempre. Convergencia continua en vez de correccion puntual.

Dos propiedades hacen que esto sea robusto ante casi cualquier tipo de
falla:

  - Se dispara por NIVEL (el estado actual), no por EVENTO (que paso
    para llegar ahi). Si se pierde un evento, la proxima pasada del
    loop igual va a notar la discrepancia comparando contra la
    realidad — no depende de haberse enterado de nada en particular.
  - Es idempotente: correr la reconciliacion muchas veces seguidas
    sobre un estado que ya coincide con lo deseado no hace nada — es
    seguro correrla todo el tiempo, sin condiciones.
"""
import random

DESIRED_REPLICAS = 3


def simulate_imperative(rng: random.Random, ticks: int, delete_probability: float) -> list:
    """Un script imperativo crea las replicas deseadas UNA sola vez, al
    principio, y nunca mas vuelve a mirar. Cualquier interferencia
    externa posterior (un nodo que muere, alguien borra un pod a mano)
    queda sin corregir para siempre.
    """
    pods = DESIRED_REPLICAS  # el "create 3 pods" inicial, ejecutado una sola vez
    history = [pods]
    for _ in range(1, ticks):
        if rng.random() < delete_probability and pods > 0:
            pods -= 1
        history.append(pods)
    return history


def simulate_reconciliation(rng: random.Random, ticks: int, delete_probability: float) -> list:
    """Cada tick, sin importar que paso antes, se compara la cantidad
    real de pods contra `DESIRED_REPLICAS` y se corrige la diferencia.
    """
    pods = DESIRED_REPLICAS
    history = [pods]
    for _ in range(1, ticks):
        if rng.random() < delete_probability and pods > 0:
            pods -= 1
        diff = DESIRED_REPLICAS - pods
        if diff > 0:
            pods += diff
        history.append(pods)
    return history


def simulate_edge_triggered(rng: random.Random, ticks: int, delete_probability: float, event_drop_probability: float) -> list:
    """Un controlador que reacciona a EVENTOS especificos ("se borro un
    pod") en vez de mirar el estado real. Si el evento se pierde (una
    desconexion del watch, un controlador que se reinicio justo en ese
    momento), el controlador nunca se entera de que hace falta
    reponer nada.
    """
    real_pods = DESIRED_REPLICAS
    history = [real_pods]
    for _ in range(1, ticks):
        if rng.random() < delete_probability and real_pods > 0:
            real_pods -= 1
            if rng.random() > event_drop_probability:
                real_pods += 1  # el evento SI llego: se repone de inmediato
        history.append(real_pods)
    return history
