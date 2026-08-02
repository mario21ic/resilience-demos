"""Productor rapido + consumidor lento, conectados por una cola.

`run_pipeline` corre el mismo productor y el mismo consumidor sobre
una cola dada (acotada o no) y devuelve metricas: cuando termino de
PRODUCIR todo, cuando termino de CONSUMIR todo, el tamano maximo que
alcanzo la cola, y una serie de muestras de tamano en el tiempo.

Si la cola tiene `maxsize`, `queue.Queue.put()` BLOQUEA cuando esta
llena — ese bloqueo es la backpressure en si misma: el productor no
puede seguir generando trabajo mas rapido de lo que el consumidor lo
retira.
"""
import queue
import threading
import time


def _producer(q: "queue.Queue", n_items: int, interval: float, stats: dict):
    for i in range(n_items):
        q.put(i)  # bloquea aca si `q` tiene maxsize y esta llena
        stats["produced"] = i + 1
        time.sleep(interval)
    stats["produce_finished_at"] = time.monotonic() - stats["start"]


def _consumer(q: "queue.Queue", n_items: int, interval: float, stats: dict):
    for i in range(n_items):
        q.get()
        time.sleep(interval)  # simula el trabajo real de procesar el item
        stats["consumed"] = i + 1
    stats["consume_finished_at"] = time.monotonic() - stats["start"]


def run_pipeline(
    q: "queue.Queue",
    n_items: int,
    produce_interval: float,
    consume_interval: float,
    sample_interval: float = 0.3,
) -> dict:
    stats = {"start": time.monotonic(), "produced": 0, "consumed": 0}
    samples = []

    producer_thread = threading.Thread(target=_producer, args=(q, n_items, produce_interval, stats))
    consumer_thread = threading.Thread(target=_consumer, args=(q, n_items, consume_interval, stats))

    producer_thread.start()
    consumer_thread.start()

    while producer_thread.is_alive() or consumer_thread.is_alive():
        elapsed = time.monotonic() - stats["start"]
        samples.append((elapsed, q.qsize(), stats["produced"], stats["consumed"]))
        time.sleep(sample_interval)

    producer_thread.join()
    consumer_thread.join()

    return {
        "samples": samples,
        "produce_finished_at": stats["produce_finished_at"],
        "consume_finished_at": stats["consume_finished_at"],
        "max_queue_size": max((s[1] for s in samples), default=0),
    }
