"""Event sourcing: en vez de guardar el estado ACTUAL de algo y
mutarlo en el lugar, se guarda la secuencia completa de EVENTOS que
llevaron a ese estado (un log de solo-agregar). El estado nunca es la
fuente de verdad — es una PROYECCION, calculada aplicando los eventos
en orden ("fold" / "reduce").

La consecuencia central: si el estado derivado se corrompe (un bug,
una migracion mal hecha, un error humano que lo pisa), se puede tirar
a la basura y reconstruir desde cero reproduciendo el log — siempre
que el log en si este intacto. El log es lo unico que realmente hay
que proteger.
"""


class EventLog:
    def __init__(self):
        self.events: list = []

    def append(self, event_type: str, payload: dict):
        self.events.append((event_type, payload))


def project_balance(events: list, start_balance: float = 0.0) -> float:
    """Una proyeccion: el saldo actual, calculado aplicando cada
    evento en orden. Se puede correr desde el evento 0, o desde un
    punto intermedio si ya se tiene un `start_balance` de un snapshot.
    """
    balance = start_balance
    for event_type, payload in events:
        if event_type == "Deposited":
            balance += payload["amount"]
        elif event_type == "Withdrawn":
            balance -= payload["amount"]
    return balance


def project_transaction_counts(events: list) -> dict:
    """Otra proyeccion DISTINTA sobre el MISMO log — no hizo falta
    cambiar nada de como se registran los eventos para poder agregar
    esta vista nueva.
    """
    counts: dict = {}
    for event_type, _ in events:
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def project_total_deposits(events: list) -> float:
    """Una tercera proyeccion: cuanto entro en total, sin importar
    cuanto se retiro despues. Util para reportes que el diseño
    original del sistema nunca previo."""
    return sum(payload["amount"] for event_type, payload in events if event_type == "Deposited")
