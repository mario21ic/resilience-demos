"""Demo del patron de resiliencia: Load shedding.

El [throttling](../4-throttling) encola el exceso y lo demora. El load
shedding no encola nada: cuando el sistema esta cerca de su capacidad,
decide EN EL ACTO si admite o rechaza cada request, y lo hace teniendo
en cuenta su prioridad — para que, si hay que sacrificar trafico, se
sacrifique primero el menos importante.

Este demo compara dos formas de rechazar bajo sobrecarga, con la
MISMA secuencia de llegada: primero una rafaga de trafico de baja
prioridad (`sheddable`), despues trafico normal (`default`), y recien
al final trafico critico (`critical`) — la situacion real donde
trafico de fondo (batch, prefetch, analytics) satura el sistema justo
antes de que llegue trafico importante:

  Sin prioridad: se admite estrictamente por orden de llegada hasta
                 llenar la capacidad (FIFO). Quien llega primero se
                 queda con el lugar, sin importar su importancia.
  Con prioridad: `sheddable` se corta al 50% de uso, `default` al 80%,
                 `critical` recien al 100% — dejando margen reservado
                 para lo mas importante, sin importar cuando llega.

Parte 2 valida el mismo comportamiento contra un endpoint HTTP real.
"""
import threading
import time
import urllib.error
import urllib.request

from load_shedder import LoadShedder
from server import start_server

HOST, PORT = "localhost", 8773
BASE_URL = f"http://{HOST}:{PORT}/"

CAPACITY = 10
WAVES = [("sheddable", 7), ("default", 6), ("critical", 4)]


# --- Parte 1: FIFO sin prioridad vs. shedding por prioridad ---------------


def run_wave_sequence(shedder: LoadShedder) -> dict:
    """Aplica las tres oleadas en orden, SIN liberar nunca los cupos
    admitidos — simula que todos los requests previos siguen en curso
    cuando llega la siguiente oleada.
    """
    results = {}
    for priority, count in WAVES:
        admitted = sum(1 for _ in range(count) if shedder.try_admit(priority))
        results[priority] = (admitted, count)
    return results


def print_part1():
    print("Parte 1: misma secuencia de llegada (sheddable -> default -> critical), capacidad=10\n")

    naive = LoadShedder(capacity=CAPACITY, thresholds={"sheddable": 1.0, "default": 1.0, "critical": 1.0})
    aware = LoadShedder(capacity=CAPACITY)  # umbrales por defecto: 0.5 / 0.8 / 1.0

    naive_results = run_wave_sequence(naive)
    aware_results = run_wave_sequence(aware)

    header = f"{'prioridad':>10} | {'sin prioridad (FIFO)':>24} | {'con prioridad (shedding por clase)':>36}"
    print(header)
    print("-" * len(header))
    for priority, count in WAVES:
        na, nt = naive_results[priority]
        aa, at = aware_results[priority]
        print(f"{priority:>10} | {f'{na}/{nt} admitidos':>24} | {f'{aa}/{at} admitidos':>36}")
    print()
    print("Sin prioridad, 'sheddable' se queda con casi toda la capacidad solo por haber")
    print("llegado primero, y 'critical' se rechaza por completo al llegar tarde.")
    print("Con prioridad, 'sheddable' cede parte de esa capacidad y 'critical' consigue")
    print("lugar aunque el sistema ya estuviera muy cargado cuando llego.\n")


# --- Parte 2: mismo comportamiento contra un endpoint HTTP real ----------


def call_work(priority: str, results: list, lock: threading.Lock):
    url = f"{BASE_URL}api/work?priority={priority}"
    try:
        with urllib.request.urlopen(url, timeout=5.0) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    with lock:
        results.append((priority, status))


def print_part2():
    print("Parte 2: la misma secuencia contra el endpoint HTTP real (capacidad=10)\n")

    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    results = []
    lock = threading.Lock()
    threads = []
    for priority, count in WAVES:
        for _ in range(count):
            t = threading.Thread(target=call_work, args=(priority, results, lock))
            threads.append(t)
            t.start()
            time.sleep(0.02)  # preserva el orden de llegada entre oleadas

    for t in threads:
        t.join()

    for priority, _ in WAVES:
        subset = [r for r in results if r[0] == priority]
        admitted = sum(1 for _, status in subset if status == 200)
        print(f"  {priority:>10}: {admitted}/{len(subset)} admitidos (200), resto rechazado (503)")

    server.shutdown()


def main():
    print_part1()
    print_part2()


if __name__ == "__main__":
    main()
