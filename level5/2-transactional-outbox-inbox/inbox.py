"""Transactional inbox: el espejo del outbox, del lado del consumidor.

Si un mensaje se puede entregar mas de una vez (at-least-once, la
garantia tipica de un broker real), aplicar su efecto de negocio y
"marcarlo como procesado" tambien tienen que ser la MISMA transaccion
— si no, un consumidor puede aplicar el efecto dos veces (si la marca
de procesado falla despues) o marcarlo como procesado sin haber
terminado de aplicarlo (si el proceso muere a mitad de camino).

Este es solo un adelanto minimo: la deduplicacion de consumidores en
profundidad (distintas estrategias, no solo esta tabla) se ve en
[3-consumidor-idempotente-dedup](../3-consumidor-idempotente-dedup).
"""
import sqlite3


def setup_consumer_database() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE account_balance (id TEXT PRIMARY KEY, balance REAL)")
    conn.execute("INSERT INTO account_balance VALUES ('acc-1', 0)")
    conn.execute("CREATE TABLE inbox (message_id TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def handle_message_with_inbox(conn: sqlite3.Connection, message_id: str, amount: float) -> bool:
    """Aplica el deposito solo si `message_id` no se proceso antes. La
    insercion en `inbox` y la actualizacion del saldo van en la misma
    transaccion: si el mensaje ya esta en `inbox` (llave primaria
    duplicada), la transaccion entera se aborta y el saldo no cambia.

    Devuelve True si se aplico el efecto, False si era un duplicado.
    """
    try:
        with conn:
            conn.execute("INSERT INTO inbox (message_id) VALUES (?)", (message_id,))
            conn.execute(
                "UPDATE account_balance SET balance = balance + ? WHERE id = 'acc-1'", (amount,)
            )
        return True
    except sqlite3.IntegrityError:
        return False  # ya se habia procesado este mensaje: se ignora sin tocar el saldo
