"""Demo: Transactional outbox / inbox.

  Parte 1 — El problema: escribir en la base y publicar un evento como
            dos operaciones separadas. Si el broker esta caido
            justo en ese momento, la orden queda guardada pero el
            evento nunca sale — nadie se entera.
  Parte 2 — La solucion: el evento se escribe en una tabla "outbox"
            DENTRO de la misma transaccion que el cambio de negocio.
            Un relay separado la drena hacia el broker real,
            reintentando hasta que confirme — nunca se pierde nada,
            pase lo que pase con el broker.
  Parte 3 — El espejo del lado del consumidor: una tabla "inbox" hace
            que aplicar un mensaje sea idempotente, aunque el broker
            lo entregue mas de una vez.
"""
from broker import FakeBroker
from inbox import handle_message_with_inbox, setup_consumer_database
from outbox import create_order_naive, create_order_with_outbox, relay_outbox, setup_database


def demo_naive_dual_write():
    print("=" * 70)
    print("Parte 1: sin outbox — escribir y publicar son dos pasos separados")
    print("=" * 70)

    conn = setup_database()
    broker = FakeBroker()
    broker.available = False  # el broker esta caido justo cuando llega el pedido

    try:
        create_order_naive(conn, broker, "ORD-1", 100.0)
    except Exception as exc:
        print(f"  publish() fallo: {exc}")

    orders = conn.execute("SELECT * FROM orders").fetchall()
    print(f"  ordenes en la base: {orders}")
    print(f"  eventos publicados: {broker.published}")
    print("  -> la orden existe, pero NINGUN servicio se entero de que se creo.")
    print("     no hay forma de reparar esto reintentando 'publicar el evento':")
    print("     el codigo que la creo ya termino y no sabe que hace falta reintentar.\n")


def demo_outbox_relay():
    print("=" * 70)
    print("Parte 2: con outbox — la escritura y el evento son atomicos")
    print("=" * 70)

    conn = setup_database()
    broker = FakeBroker()
    broker.available = False  # el broker sigue caido al momento de crear la orden

    create_order_with_outbox(conn, "ORD-2", 250.0)

    orders = conn.execute("SELECT * FROM orders").fetchall()
    pending = conn.execute("SELECT event_type, payload, published FROM outbox").fetchall()
    print(f"  ordenes en la base: {orders}")
    print(f"  outbox (todavia sin publicar, porque el broker esta caido): {pending}")

    print("\n  intento de relay #1 (el broker sigue caido):")
    published = relay_outbox(conn, broker)
    print(f"    -> {published} eventos publicados, sigue pendiente en la outbox")

    print("\n  el broker se recupera...")
    broker.available = True

    print("  intento de relay #2:")
    published = relay_outbox(conn, broker)
    print(f"    -> {published} eventos publicados")
    print(f"    -> eventos en el broker: {broker.published}")
    print("  -> la orden nunca se perdio Y el evento nunca se perdio, aunque el broker")
    print("     haya estado caido justo en el momento en que la orden se creo.\n")


def demo_inbox_dedup():
    print("=" * 70)
    print("Parte 3: con inbox — aplicar el mismo mensaje dos veces no duplica el efecto")
    print("=" * 70)

    conn = setup_consumer_database()

    print("  el broker entrega el mismo mensaje DOS veces (redelivery, at-least-once):")
    first = handle_message_with_inbox(conn, message_id="evt-abc-123", amount=50.0)
    second = handle_message_with_inbox(conn, message_id="evt-abc-123", amount=50.0)

    balance = conn.execute("SELECT balance FROM account_balance WHERE id='acc-1'").fetchone()[0]
    print(f"    primera entrega: {'aplicada' if first else 'ignorada (duplicado)'}")
    print(f"    segunda entrega: {'aplicada' if second else 'ignorada (duplicado)'}")
    print(f"    saldo final: {balance} (deberia ser 50, no 100)")


def main():
    demo_naive_dual_write()
    demo_outbox_relay()
    demo_inbox_dedup()


if __name__ == "__main__":
    main()
