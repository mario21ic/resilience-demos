"""Simulaciones de topologia de redundancia: activo-activo vs
activo-pasivo, cada una con distintos niveles de redundancia (N+1,
N+2).

Son dos preguntas independientes:

  - CUANTA capacidad de sobra hay (N+1 tolera UNA falla simultanea sin
    perder capacidad; N+2 tolera DOS).
  - COMO esta organizada esa capacidad de sobra: sirviendo trafico
    todo el tiempo (activo-activo) o de guardia sin servir nada hasta
    que se la promueve (activo-pasivo).

No hay red ni threads: es una simulacion de eventos discretos en
"ticks" de tiempo, para poder razonar limpiamente sobre cuanta
capacidad sobrevive a cada falla y cuanto tarda cada topologia en
reaccionar.
"""
from dataclasses import dataclass


@dataclass
class Tick:
    t: int
    demand: int
    capacity: int
    dropped: int
    note: str = ""


def simulate_active_active(
    total_instances: int,
    capacity_per_instance: int,
    demand: int,
    failures: dict[int, int],
    ticks: int,
) -> list[Tick]:
    """`failures`: {tick: cuantas instancias fallan en ese tick}. Las
    instancias caidas no se recuperan en esta simulacion. Todas las
    instancias sanas comparten la demanda por igual (load balancing
    ideal); si la capacidad total no alcanza, el faltante se pierde.
    """
    healthy = total_instances
    timeline = []
    for t in range(ticks):
        note = ""
        if t in failures:
            healthy -= failures[t]
            note = f"falla(n) {failures[t]} instancia(s) -> quedan {healthy}/{total_instances} sanas"

        capacity = max(0, healthy) * capacity_per_instance
        dropped = max(0, demand - capacity)
        timeline.append(Tick(t, demand, capacity, dropped, note))
    return timeline


def simulate_active_passive(
    n_spares: int,
    failover_delay: int,
    demand: int,
    failures: set[int],
    ticks: int,
) -> list[Tick]:
    """`failures`: ticks en los que falla quien esta activo en ese
    momento. Cada falla consume un spare (si hay) e inicia un
    failover de `failover_delay` ticks, durante el cual la capacidad
    es CERO (a diferencia de activo-activo, ahi no hay degradacion
    parcial: o esta activo el que sirve, o no hay nadie sirviendo).
    Si no quedan spares, la caida es permanente (hasta intervencion
    manual, fuera del alcance de esta simulacion).
    """
    spares_left = n_spares
    failover_remaining = 0
    permanently_down = False
    timeline = []

    for t in range(ticks):
        note = ""
        if t in failures and not permanently_down:
            if spares_left > 0:
                spares_left -= 1
                failover_remaining = failover_delay
                note = f"falla el activo -> failover en curso ({spares_left} spare(s) restantes)"
            else:
                permanently_down = True
                note = "falla el activo -> SIN spares restantes, caida permanente"

        if permanently_down:
            capacity = 0
        elif failover_remaining > 0:
            capacity = 0
            failover_remaining -= 1
            if failover_remaining == 0:
                note = (note + " / failover completo, spare promovido a activo").strip(" /")
        else:
            capacity = demand  # el activo cubre el 100% de la demanda cuando esta sano

        dropped = max(0, demand - capacity)
        timeline.append(Tick(t, demand, capacity, dropped, note))

    return timeline
