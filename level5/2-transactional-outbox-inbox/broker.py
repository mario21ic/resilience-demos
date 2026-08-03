"""Un "broker" de mensajes simulado: guarda los eventos que efectivamente
se publicaron, y puede configurarse para fallar (representando una
caida temporal del broker real)."""


class BrokerUnavailable(Exception):
    pass


class FakeBroker:
    def __init__(self):
        self.published: list = []
        self.available = True

    def publish(self, event_type: str, payload: str):
        if not self.available:
            raise BrokerUnavailable("el broker no esta disponible ahora mismo")
        self.published.append((event_type, payload))
