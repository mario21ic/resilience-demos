"""Demo: Consumidor idempotente / deduplicacion.

  Parte 1 — El problema sin nada: una operacion NO idempotente (sumar
            un delta) aplicada dos veces por una redelivery duplica el
            efecto de negocio.
  Parte 2 — Deduplicacion con ventana (TTL): cuantifica cuantas
            redeliveries se cuelan igual segun el tamaño de la
            ventana, contra una distribucion realista de demoras de
            redelivery (mayoria rapidas, algunas muy tardias).
  Parte 3 — Idempotencia natural: rediseñar la operacion para que
            aplicarla dos veces de el mismo resultado, sin necesitar
            recordar nada — la solucion mas robusta cuando es posible.
"""
import random

from dedup import (
    NaturallyIdempotentAccount,
    NonIdempotentAccount,
    TTLDedupCache,
    draw_redelivery_delay,
)


def demo_no_dedup():
    print("=" * 70)
    print("Parte 1: sin deduplicacion, una redelivery duplica el efecto")
    print("=" * 70)

    account = NonIdempotentAccount()
    print("  mensaje 'depositar $50' entregado dos veces (redelivery normal):")
    account.apply_delta(50.0)
    print(f"    primera entrega -> saldo: {account.balance}")
    account.apply_delta(50.0)
    print(f"    segunda entrega -> saldo: {account.balance} (deberia seguir siendo 50)\n")


def demo_ttl_window():
    print("=" * 70)
    print("Parte 2: deduplicacion con ventana (TTL) — cuanto se cuela igual")
    print("=" * 70)
    print("200.000 mensajes, cada uno redisparado una vez despues de una demora")
    print("realista (mayoria rapida, 2% muy tardia).\n")

    header = f"{'ventana':>12} | {'duplicados atrapados':>20} | {'igual se aplican 2 veces':>24}"
    print(header)
    print("-" * len(header))
    for window_s, label in ((60, "1 min"), (600, "10 min"), (3600, "1 hora"), (86400, "1 dia")):
        rng = random.Random(3)
        n = 200_000
        caught = 0
        for i in range(n):
            # una cache por mensaje, cada una con su propio reloj relativo (t=0 al
            # llegar por primera vez), para no mezclar los relojes de mensajes distintos
            cache = TTLDedupCache(window_s)
            message_id = f"msg-{i}"
            cache.mark_seen(message_id, now=0.0)
            delay = draw_redelivery_delay(rng)
            if cache.is_duplicate(message_id, now=delay):
                caught += 1
        missed = n - caught
        print(f"{label:>12} | {caught / n:>19.2%} | {missed / n:>23.3%}")

    print("\nHasta una ventana de 1 hora deja pasar redeliveries igual (~1.9%) — la cola")
    print("larga de demoras (mensajes reprocesados horas o dias despues) siempre puede")
    print("superar cualquier ventana finita que sea practica de mantener en memoria.")
    print("Para operaciones donde eso es inaceptable, hace falta una tabla permanente")
    print("(ver el 'inbox' de [2-transactional-outbox-inbox](../2-transactional-outbox-inbox))")
    print("o volver la operacion naturalmente idempotente (Parte 3).\n")


def demo_natural_idempotency():
    print("=" * 70)
    print("Parte 3: idempotencia NATURAL — no hace falta recordar nada")
    print("=" * 70)

    account = NaturallyIdempotentAccount()
    print("  el mismo evento de negocio, pero el mensaje trae el SALDO FINAL")
    print("  esperado (version 1: saldo=50) en vez de un delta a sumar:\n")

    account.apply_absolute(version=1, new_balance=50.0)
    print(f"    primera entrega (version 1, saldo=50) -> saldo: {account.balance}")
    account.apply_absolute(version=1, new_balance=50.0)
    print(f"    redelivery de la MISMA version -> saldo: {account.balance} (sin cambios)")
    account.apply_absolute(version=2, new_balance=80.0)
    print(f"    version 2 legitima (otro deposito) -> saldo: {account.balance}")
    account.apply_absolute(version=1, new_balance=50.0)
    print(f"    una redelivery tardia de la version 1 vieja -> saldo: {account.balance} "
          f"(se ignora: ya se aplico una version mas nueva)")
    print("\n  no hizo falta ninguna tabla de deduplicacion ni ventana de tiempo: la")
    print("  operacion en si es idempotente por construccion, sin importar cuando")
    print("  llegue una redelivery ni cuantas veces.")


def main():
    demo_no_dedup()
    demo_ttl_window()
    demo_natural_idempotency()


if __name__ == "__main__":
    main()
