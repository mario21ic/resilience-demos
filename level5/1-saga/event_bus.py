"""Un bus de eventos minimo: cada servicio se suscribe a los eventos
que le importan y publica los suyos propios. Nadie tiene una vista
completa del flujo — cada uno solo sabe "cuando pasa X, yo hago Y".
"""


class EventBus:
    def __init__(self):
        self._subscribers: dict = {}

    def subscribe(self, event_type: str, handler):
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, ctx):
        ctx.record(f"evento: {event_type}")
        for handler in self._subscribers.get(event_type, []):
            handler(ctx)
