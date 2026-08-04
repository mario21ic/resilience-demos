"""Autoscaling: agregar o quitar capacidad segun la demanda, en vez de
provisionar siempre para el peor caso. Dos estrategias, y una
limitacion de fondo que ninguna de las dos elimina.

  - Reactivo: mide la demanda real y agrega capacidad cuando hace
    falta. Tiene un retraso inherente: tiempo de deteccion (cada
    cuanto se revisan las metricas) + tiempo de aprovisionamiento
    (cuanto tarda una instancia nueva en estar lista). Durante ese
    retraso, la demanda que ya llego y no se puede atender se pierde.
  - Predictivo: usa patrones conocidos (la hora del dia, un evento
    programado) para escalar ANTES de que la demanda suba, evitando el
    retraso — pero solo funciona para lo que se puede anticipar.

La limitacion de fondo: el autoscaling nunca puede reaccionar mas
rapido que su propio tiempo de deteccion + aprovisionamiento. Si un
incidente (una rafaga de trafico, una tormenta de reintentos) crece
mas rapido que eso, el autoscaling solo no alcanza para evitar la
perdida de capacidad — hacen falta otros mecanismos (load shedding,
circuit breakers, capacidad pre-aprovisionada) para sobrevivir la
ventana antes de que la capacidad nueva llegue.
"""

CAPACITY_PER_INSTANCE = 100.0


def simulate_reactive(demand_fn, ticks: int, detection_interval: int, provision_time: int, initial_instances: int):
    """Autoscaler reactivo: revisa la demanda cada `detection_interval`
    ticks, y si hace falta mas capacidad, la nueva instancia queda
    lista recien `provision_time` ticks despues. Devuelve la demanda
    total perdida (la que no se pudo atender por falta de capacidad).
    """
    instances = initial_instances
    pending = []
    total_dropped = 0.0

    for t in range(ticks):
        ready = [p for p in pending if p[0] <= t]
        for _, qty in ready:
            instances += qty
        pending = [p for p in pending if p[0] > t]

        demand = demand_fn(t)
        capacity = instances * CAPACITY_PER_INSTANCE
        if demand > capacity:
            total_dropped += demand - capacity

        if t % detection_interval == 0:
            needed = max(0, -(-int(demand) // int(CAPACITY_PER_INSTANCE)) - instances)
            if needed > 0:
                pending.append((t + provision_time, needed))

    return total_dropped


def simulate_predictive(demand_fn, ticks: int, provision_time: int, initial_instances: int, known_spike_tick: int, known_spike_demand: float):
    """Autoscaler predictivo: sabe DE ANTEMANO que en `known_spike_tick`
    la demanda va a subir a `known_spike_demand`, asi que dispara el
    aprovisionamiento con la anticipacion suficiente para que la
    capacidad ya este lista antes de que la demanda llegue.
    """
    instances = initial_instances
    needed = max(0, -(-int(known_spike_demand) // int(CAPACITY_PER_INSTANCE)) - initial_instances)
    pending = [(known_spike_tick, needed)] if needed > 0 else []
    total_dropped = 0.0

    for t in range(ticks):
        ready = [p for p in pending if p[0] <= t]
        for _, qty in ready:
            instances += qty
        pending = [p for p in pending if p[0] > t]

        demand = demand_fn(t)
        capacity = instances * CAPACITY_PER_INSTANCE
        if demand > capacity:
            total_dropped += demand - capacity

    return total_dropped


def exponential_demand(t: int, base: float, doubling_time: float) -> float:
    """Modela un incidente que crece exponencialmente (ej. una
    tormenta de reintentos, ver
    [level1/6-retry-budget](../../level1/6-retry-budget)): la demanda
    se duplica cada `doubling_time` ticks."""
    return base * (2 ** (t / doubling_time))
