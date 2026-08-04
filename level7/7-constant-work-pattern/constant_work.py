"""Constant work pattern (AWS): en vez de que un sistema haga POCO
trabajo en el dia a dia y MUCHO trabajo durante una crisis (un sistema
BIMODAL), se lo diseña para hacer siempre la MISMA cantidad de
trabajo, haya o no haya cambios reales que procesar.

El ejemplo clasico de AWS: en vez de propagar solo los cambios de DNS
que ocurrieron (un sistema "delta"), Route 53 reenvia periodicamente
el estado COMPLETO de todos los registros, todo el tiempo. Eso
significa que un incidente que genera muchos cambios de golpe no le
pide al sistema hacer algo nuevo — ya estaba haciendo ese volumen de
trabajo, siempre, sin excepcion.

Dos problemas que esto elimina:

  1. Capacidad: un sistema delta dimensionado para el caso normal se
     desborda ante una rafaga real; dimensionarlo para el peor caso
     desperdicia casi toda su capacidad el resto del tiempo.
  2. Confianza: el "modo crisis" de un sistema bimodal es,
     precisamente por ser raro, el camino de codigo MENOS probado —
     exactamente el que mas necesita funcionar cuando llega el
     momento.
"""


def simulate_delta_recovery(burst_size: int, capacity_per_cycle: int) -> int:
    """Un sistema delta, dimensionado para el volumen normal de
    cambios, recibe una rafaga real de `burst_size` cambios de golpe.
    Devuelve cuantos ciclos tarda en absorberla."""
    backlog = burst_size
    cycles = 0
    while backlog > 0:
        backlog -= capacity_per_cycle
        cycles += 1
    return cycles


def constant_work_cycles_to_recover(burst_size: int, total_records: int) -> int:
    """Un sistema de trabajo constante reenvia `total_records` (el
    estado completo) en cada ciclo, siempre. Mientras la rafaga quepa
    dentro de ese volumen ya habitual, no genera ningun backlog
    adicional."""
    return 0 if burst_size <= total_records else float("inf")
