"""Demo: Tolerant reader / ley de Postel.

  Parte 1 — El productor agrega un campo nuevo (evolucion aditiva,
            deberia ser inofensiva): un consumidor estricto se rompe
            igual; uno tolerante ni lo nota.
  Parte 2 — Varias evoluciones del esquema a lo largo del tiempo: el
            consumidor tolerante sobrevive a todas sin cambiar una
            linea de codigo.
  Parte 3 — El limite del patron: tolerant reader protege contra
            campos NUEVOS, no contra perder un campo que de verdad
            hace falta.
"""
from tolerant_reader import strict_consumer, tolerant_consumer, tolerant_consumer_with_default


def demo_additive_change():
    print("=" * 70)
    print("Parte 1: el productor agrega un campo — evolucion 'inofensiva'")
    print("=" * 70)

    v1_event = {"user_id": "u1", "amount": 100}
    v2_event = {"user_id": "u2", "amount": 200, "currency": "USD"}  # agrega 'currency'

    print(f"  evento original: {v1_event}")
    print(f"    consumidor estricto: {strict_consumer(v1_event)}")
    print(f"    consumidor tolerante: {tolerant_consumer(v1_event)}\n")

    print(f"  evento evolucionado (agrega 'currency'): {v2_event}")
    try:
        print(f"    consumidor estricto: {strict_consumer(v2_event)}")
    except ValueError as exc:
        print(f"    consumidor estricto: FALLA -> {exc}")
    print(f"    consumidor tolerante: {tolerant_consumer(v2_event)}\n")


def demo_multiple_evolutions():
    print("=" * 70)
    print("Parte 2: varias evoluciones del esquema, un solo consumidor tolerante")
    print("=" * 70)

    events = [
        {"user_id": "u1", "amount": 100},
        {"user_id": "u2", "amount": 200, "currency": "USD"},
        {"user_id": "u3", "amount": 300, "currency": "ARS", "channel": "mobile"},
        {"user_id": "u4", "amount": 400, "currency": "EUR", "channel": "web", "risk_score": 0.02},
    ]

    for event in events:
        print(f"  {event}")
        print(f"    -> {tolerant_consumer(event)}")
    print("\n  el mismo consumidor, sin cambios, procesa cuatro versiones distintas")
    print("  del esquema — cada una con mas campos que la anterior.\n")


def demo_limits_of_tolerance():
    print("=" * 70)
    print("Parte 3: el limite del patron — perder un campo que hace falta")
    print("=" * 70)

    print("  el productor deja de mandar 'currency' (antes lo mandaba siempre):")
    event_without_currency = {"user_id": "u5", "amount": 500}
    print(f"    {tolerant_consumer_with_default(event_without_currency)}  (uso el default 'USD')")

    print("\n  pero si el campo que falta es 'amount' (indispensable para la logica):")
    event_without_amount = {"user_id": "u6", "currency": "USD"}
    amount = event_without_amount.get("amount")
    print(f"    amount = {amount!r} -> ninguna cantidad de tolerancia arregla esto solo;")
    print("    hace falta decidir explicitamente que hacer (rechazar el evento, alertar,")
    print("    usar un valor de negocio con sentido) — tolerant reader evita crashes por")
    print("    campos NUEVOS, no reemplaza la validacion de los campos que si importan.")


def main():
    demo_additive_change()
    demo_multiple_evolutions()
    demo_limits_of_tolerance()


if __name__ == "__main__":
    main()
