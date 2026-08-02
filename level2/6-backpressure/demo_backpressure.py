"""Demo del patron de resiliencia: Backpressure.

El [load shedding](../5-load-shedding) y el [throttling](../4-throttling)
son decisiones UNILATERALES de quien recibe el trabajo: rechazar o
demorar, sin que el productor necesariamente se entere ni cambie su
comportamiento. El backpressure es distinto: es una señal que viaja
hacia ATRAS en la cadena, del consumidor hacia el productor, para que
el productor mismo reduzca su ritmo — cooperacion entre las dos
puntas, no una decision unilateral de una sola.

La forma mas simple y universal de backpressure es una cola ACOTADA:
si el productor intenta agregar un item y la cola ya esta llena, la
operacion de encolar BLOQUEA hasta que el consumidor libere lugar. Ese
bloqueo es la señal en si misma — el productor no puede avanzar mas
rapido de lo que el consumidor retira trabajo.

Este demo tiene dos partes:

  Parte 1: un productor rapido y un consumidor lento conectados por
           una cola SIN limite vs. una cola CON limite, mostrando como
           cambia el comportamiento del PRODUCTOR (no solo el tamano
           de la cola) segun haya o no backpressure.
  Parte 2: la variante "pull" del mismo problema, con un generador en
           vez de una cola — el productor literalmente no puede
           adelantarse porque su codigo no corre hasta que alguien le
           pide el siguiente valor.
"""
import queue
import time

from pipeline import run_pipeline

N_ITEMS = 40
PRODUCE_INTERVAL = 0.01  # productor rapido: un item cada 10ms
CONSUME_INTERVAL = 0.08  # consumidor lento: un item cada 80ms


def print_scenario(result: dict):
    print(f"  {'t(s)':>6} | {'tamano de cola':>14} | {'producidos':>10} | {'consumidos':>10}")
    for elapsed, qsize, produced, consumed in result["samples"]:
        print(f"  {elapsed:>6.2f} | {qsize:>14} | {produced:>10} | {consumed:>10}")
    print(
        f"  -> productor termino en {result['produce_finished_at']:.2f}s, "
        f"consumidor termino en {result['consume_finished_at']:.2f}s, "
        f"tamano maximo de cola: {result['max_queue_size']}\n"
    )


def demo_bounded_vs_unbounded():
    print(
        f"Productor rapido (cada {PRODUCE_INTERVAL * 1000:.0f}ms) vs. consumidor lento "
        f"(cada {CONSUME_INTERVAL * 1000:.0f}ms), {N_ITEMS} items.\n"
    )

    print("=" * 70)
    print("Escenario 1: cola SIN limite (sin backpressure)")
    print("=" * 70)
    unbounded = run_pipeline(queue.Queue(), N_ITEMS, PRODUCE_INTERVAL, CONSUME_INTERVAL)
    print_scenario(unbounded)

    print("=" * 70)
    print("Escenario 2: cola CON limite de 5 (con backpressure)")
    print("=" * 70)
    bounded = run_pipeline(queue.Queue(maxsize=5), N_ITEMS, PRODUCE_INTERVAL, CONSUME_INTERVAL)
    print_scenario(bounded)

    print(
        f"Sin backpressure, el productor termina en {unbounded['produce_finished_at']:.2f}s "
        f"(su ritmo nativo) y deja hasta {unbounded['max_queue_size']} items pendientes en la cola:"
    )
    print("memoria y latencia acumulada que crecen sin que el productor se entere.\n")
    print(
        f"Con backpressure, el productor tarda {bounded['produce_finished_at']:.2f}s en terminar "
        f"— casi lo mismo que el consumidor ({bounded['consume_finished_at']:.2f}s) — porque se"
    )
    print(f"frena solo, bloqueado en cada `put()`, y la cola nunca supera su limite (max {bounded['max_queue_size']}).")


def demo_pull_based():
    print("\n" + "=" * 70)
    print("Parte 2: backpressure 'pull' con un generador (sin colas ni threads)")
    print("=" * 70)
    print("El productor es un generador: su codigo no avanza hasta que el")
    print("consumidor le pide el siguiente valor con next() — no hace falta")
    print("bloquear nada porque el productor nunca puede adelantarse.\n")

    def producer_gen():
        for i in range(5):
            print(f"    productor: generando item {i}")
            yield i

    for item in producer_gen():
        print(f"    consumidor: procesando item {item}")
        time.sleep(0.1)


def main():
    demo_bounded_vs_unbounded()
    demo_pull_based()


if __name__ == "__main__":
    main()
