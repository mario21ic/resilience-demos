"""Tolerant reader / ley de Postel: "se conservador en lo que envias,
liberal en lo que aceptas". Un consumidor de mensajes o respuestas de
API deberia extraer solo los campos que REALMENTE necesita e ignorar
el resto — no fallar solo porque el productor agrego un campo nuevo
que a este consumidor no le importa.

Sin esto, cualquier evolucion aditiva del esquema (agregar un campo,
algo que en teoria "no deberia romper nada") obliga a actualizar a
TODOS los consumidores en simultaneo con el productor — exactamente
el tipo de despliegue en lockstep que la independencia entre
servicios deberia evitar.
"""


def strict_consumer(event: dict) -> str:
    """Valida que el evento tenga EXACTAMENTE las claves esperadas — ni
    una de mas, ni una de menos. Cualquier campo nuevo agregado por el
    productor rompe a este consumidor, aunque nunca lo hubiera usado.
    """
    expected_keys = {"user_id", "amount"}
    if set(event.keys()) != expected_keys:
        raise ValueError(f"esquema inesperado: se esperaba {expected_keys}, llego {set(event.keys())}")
    return f"procesando pago de {event['user_id']} por {event['amount']}"


def tolerant_consumer(event: dict) -> str:
    """Extrae solo lo que necesita e ignora cualquier otro campo,
    presente o futuro."""
    user_id = event.get("user_id")
    amount = event.get("amount")
    return f"procesando pago de {user_id} por {amount}"


def tolerant_consumer_with_default(event: dict) -> str:
    """Tolerante tambien a que un campo que antes existia haya
    desaparecido: usa un valor por defecto en vez de fallar. Esto NO
    protege contra perder un campo que es indispensable para la
    logica de negocio — solo evita un crash cuando es razonable seguir
    sin el.
    """
    user_id = event.get("user_id")
    amount = event.get("amount")
    currency = event.get("currency", "USD")  # valor por defecto si no viene
    return f"procesando pago de {user_id} por {amount} {currency}"
