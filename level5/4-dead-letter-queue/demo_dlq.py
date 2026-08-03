"""Demo: Dead Letter Queue + reproceso y manejo de poison pills.

  Parte 1 — El problema: un mensaje "envenenado" (falla siempre)
            bloquea a todos los mensajes buenos que estan detras en
            una cola FIFO.
  Parte 2 — La DLQ: tras un maximo de intentos, el mensaje
            problematico se aisla y el resto de la cola sigue.
  Parte 3 — Reprocesar la DLQ: reintentar despues de arreglar la causa
            raiz funciona; reintentar sin arreglarla no — la DLQ
            aisla el problema, no lo resuelve sola.
"""
from dlq import build_queue, reprocess_dlq, simulate_with_dlq, simulate_without_dlq

N_GOOD_MESSAGES = 20
POISON_POSITION = 5


def demo_poison_pill_blocks_queue():
    print("=" * 70)
    print("Parte 1: un mensaje envenenado bloquea toda la cola detras de el")
    print("=" * 70)

    queue = build_queue(N_GOOD_MESSAGES, POISON_POSITION)
    processed, remaining = simulate_without_dlq(queue, max_ticks=100)

    print(f"  mensajes buenos: {N_GOOD_MESSAGES}, mensaje envenenado en la posicion {POISON_POSITION}")
    print(f"  procesados en 100 intentos: {len(processed)}/{N_GOOD_MESSAGES}")
    print(f"  quedan atascados en la cola: {len(remaining)}")
    print(f"  intentos gastados reintentando el mismo mensaje envenenado: {remaining[0].attempts if remaining else 0}")
    print("  -> los mensajes buenos que llegaron DESPUES del envenenado nunca se")
    print("     procesan, aunque no tengan absolutamente nada de malo.\n")


def demo_dlq_unblocks_queue():
    print("=" * 70)
    print("Parte 2: con DLQ, el envenenado se aisla y la cola sigue")
    print("=" * 70)

    queue = build_queue(N_GOOD_MESSAGES, POISON_POSITION)
    processed, remaining, dead_letters = simulate_with_dlq(queue, max_ticks=100, max_attempts=3)

    print(f"  procesados: {len(processed)}/{N_GOOD_MESSAGES}")
    print(f"  quedan en la cola principal: {len(remaining)}")
    print(f"  en la dead letter queue: {dead_letters}")
    print("  -> los 20 mensajes buenos se procesaron con normalidad; el envenenado")
    print("     quedo aislado, con el motivo del fallo guardado para investigar.\n")

    return dead_letters


def demo_reprocess_dlq(dead_letters):
    print("=" * 70)
    print("Parte 3: reprocesar la DLQ — con y sin arreglar la causa raiz")
    print("=" * 70)

    print("  reintento SIN arreglar el bug (el payload sigue siendo invalido):")
    recovered, still_dead = reprocess_dlq(dead_letters, bug_fixed=False)
    print(f"    recuperados: {recovered}")
    print(f"    siguen en la DLQ: {still_dead}")
    print("    -> vuelve exactamente al mismo lugar, con un intento mas acumulado.\n")

    print("  reintento DESPUES de arreglar el bug (el payload ya se corrigio):")
    recovered, still_dead = reprocess_dlq(dead_letters, bug_fixed=True)
    print(f"    recuperados: {recovered}")
    print(f"    siguen en la DLQ: {still_dead}")
    print("    -> ahora si se procesa con exito. La DLQ aisla el problema; arreglar")
    print("       la causa raiz es lo que efectivamente lo resuelve.")


def main():
    demo_poison_pill_blocks_queue()
    dead_letters = demo_dlq_unblocks_queue()
    demo_reprocess_dlq(dead_letters)


if __name__ == "__main__":
    main()
