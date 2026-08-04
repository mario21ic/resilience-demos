"""Leases y heartbeats: la forma mas comun de detectar que un nodo
sigue vivo es que mande una señal periodica ("heartbeat"), y
considerarlo caido si esa señal no llega dentro de un tiempo esperado
(un lease, ver [1-leader-election-fencing-tokens](../1-leader-election-fencing-tokens)).

El problema de un timeout FIJO: la red real tiene jitter — variacion
normal en cuanto tardan los heartbeats en llegar. Un timeout fijo
tiene que elegir entre ser generoso (tarda en detectar caidas reales)
o agresivo (genera falsas alarmas cada vez que el jitter normal supera
el umbral).

El **phi accrual failure detector** (usado en Cassandra y Akka)
resuelve esto de forma adaptativa: en vez de una decision binaria
"vivo/muerto" con un umbral fijo, calcula un valor continuo `phi` que
representa que tan SORPRENDENTE es no haber recibido un heartbeat en
este tiempo, dado el HISTORIAL de intervalos observados para ese nodo
en particular. Si los heartbeats de ese nodo siempre fueron muy
regulares, una demora chica ya genera un phi alto (sospechoso). Si
siempre fueron variables, el mismo retraso genera un phi mas bajo
(tolerado) — el detector se adapta solo a cuan ruidosa es la señal de
cada nodo.
"""
import math
import statistics


class PhiAccrualDetector:
    def __init__(self, window_size: int = 100, min_std_dev: float = 0.1):
        self.window_size = window_size
        self.min_std_dev = min_std_dev
        self.intervals: list = []
        self.last_heartbeat_time = None

    def heartbeat(self, now: float):
        if self.last_heartbeat_time is not None:
            interval = now - self.last_heartbeat_time
            self.intervals.append(interval)
            if len(self.intervals) > self.window_size:
                self.intervals.pop(0)
        self.last_heartbeat_time = now

    def phi(self, now: float) -> float:
        """Calcula phi asumiendo que los intervalos historicos siguen
        una distribucion normal (mean, std_dev). `phi` es
        `-log10(P(el nodo siga vivo dado que paso este tiempo sin
        heartbeat))` — crece sin limite cuanto mas tiempo pasa sin
        noticias, mas rapido cuanto mas regular fue el historial.
        """
        if self.last_heartbeat_time is None or len(self.intervals) < 2:
            return 0.0

        mean = statistics.mean(self.intervals)
        std_dev = max(statistics.stdev(self.intervals), self.min_std_dev)
        elapsed = now - self.last_heartbeat_time

        y = (elapsed - mean) / (std_dev * math.sqrt(2))
        cdf = 0.5 * (1 + math.erf(y))
        probability_still_alive = max(1 - cdf, 1e-16)

        return -math.log10(probability_still_alive)
