"""Transactional outbox: escribir el cambio de estado y el evento que
lo anuncia en la MISMA transaccion de base de datos, para que sea
imposible que uno ocurra sin el otro.

Sin esto, "guardar en la base y despues publicar un evento" son dos
operaciones independientes: si la segunda falla despues de que la
primera tuvo exito (o viceversa), el sistema queda en un estado
inconsistente que nadie puede reparar solo con reintentar (ver
[level1/2-retry](../../level1/2-retry) — un retry no sirve si no se
sabe cual de las dos mitades hay que repetir).

La solucion: en vez de publicar directamente, se inserta una fila en
una tabla "outbox" DENTRO de la misma transaccion que el cambio de
negocio. Como es la misma transaccion, sqlite (o cualquier base real)
garantiza que ambas escrituras se confirman juntas o ninguna lo hace.
Un proceso separado (el "relay") lee filas no publicadas de la outbox
y las manda al broker real, marcandolas como publicadas recien cuando
el broker confirma.
"""
import sqlite3

from broker import BrokerUnavailable, FakeBroker


def setup_database() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, amount REAL)")
    conn.execute(
        "CREATE TABLE outbox ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "event_type TEXT, payload TEXT, published INTEGER DEFAULT 0)"
    )
    conn.commit()
    return conn


def create_order_naive(conn: sqlite3.Connection, broker: FakeBroker, order_id: str, amount: float):
    """Sin outbox: dos operaciones independientes. Si la segunda falla,
    la primera ya quedo confirmada — inconsistencia real, no un
    problema teorico.
    """
    with conn:
        conn.execute("INSERT INTO orders (id, amount) VALUES (?, ?)", (order_id, amount))
    # esto ya es una operacion SEPARADA: si falla, la orden ya existe sin evento
    broker.publish("OrderCreated", order_id)


def create_order_with_outbox(conn: sqlite3.Connection, order_id: str, amount: float):
    """Con outbox: ambas escrituras van en la MISMA transaccion. No hay
    forma de que una se confirme sin la otra.
    """
    with conn:
        conn.execute("INSERT INTO orders (id, amount) VALUES (?, ?)", (order_id, amount))
        conn.execute(
            "INSERT INTO outbox (event_type, payload) VALUES (?, ?)",
            ("OrderCreated", order_id),
        )


def relay_outbox(conn: sqlite3.Connection, broker: FakeBroker) -> int:
    """El proceso separado que drena la outbox: por cada fila no
    publicada, intenta mandarla al broker real y recien la marca como
    publicada si el broker confirma. Si el broker sigue caido, la fila
    queda pendiente para el proximo intento — nunca se pierde.

    Devuelve cuantas filas logro publicar en esta pasada.
    """
    pending = conn.execute(
        "SELECT id, event_type, payload FROM outbox WHERE published = 0 ORDER BY id"
    ).fetchall()

    published_count = 0
    for row_id, event_type, payload in pending:
        try:
            broker.publish(event_type, payload)
        except BrokerUnavailable:
            continue  # se reintenta en la proxima pasada, la fila sigue pendiente
        with conn:
            conn.execute("UPDATE outbox SET published = 1 WHERE id = ?", (row_id,))
        published_count += 1

    return published_count
