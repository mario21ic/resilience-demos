"""Consumidor idempotente / deduplicacion: la otra mitad del
at-least-once.

Ningun broker real ofrece "exactly-once" a nivel de entrega — lo que
ofrecen es *at-least-once* (puede redisparar un mensaje ya entregado:
un ack que se perdio, un consumidor que se cayo justo despues de
procesar pero antes de confirmar) o *at-most-once* (puede perder
mensajes, nunca duplicarlos). "Exactly-once" como EXPERIENCIA solo se
consigue combinando at-least-once con un consumidor idempotente: da
igual cuantas veces llegue el mismo mensaje, el efecto final es como
si hubiera llegado una sola vez.

Este modulo compara tres formas de lograrlo:

  1. Sin nada: la operacion no es idempotente y no hay deduplicacion
     -> cada redelivery duplica el efecto.
  2. Deduplicacion con ventana (TTL): se recuerdan los IDs vistos
     recientemente, con vencimiento — barato, pero una redelivery muy
     tardia (fuera de la ventana) igual se cuela.
  3. Idempotencia NATURAL: la operacion en si se redisena para que
     aplicarla dos veces de una el mismo resultado que aplicarla una
     — no hace falta recordar nada.
"""
import random


class NonIdempotentAccount:
    """Modela el efecto NO idempotente clasico: sumar un delta. Aplicar
    el mismo mensaje dos veces duplica el efecto."""

    def __init__(self):
        self.balance = 0.0

    def apply_delta(self, amount: float):
        self.balance += amount


class NaturallyIdempotentAccount:
    """La misma operacion de negocio, pero expresada de forma que
    aplicarla dos veces con el MISMO mensaje da el mismo resultado:
    en vez de "sumar", el mensaje trae el saldo FINAL esperado despues
    de esa operacion (una version, no un delta) — repetirla no cambia
    nada.
    """

    def __init__(self):
        self.balance = 0.0
        self._last_applied_version = -1

    def apply_absolute(self, version: int, new_balance: float):
        if version <= self._last_applied_version:
            return  # ya se aplico esta version (o una posterior); no hace nada
        self.balance = new_balance
        self._last_applied_version = version


class TTLDedupCache:
    """Recuerda IDs de mensajes ya procesados durante `window_s`
    segundos. Barato (un dict), pero solo protege dentro de la
    ventana: una redelivery mas tardia que eso ya no se reconoce como
    duplicado.
    """

    def __init__(self, window_s: float):
        self.window_s = window_s
        self._seen: dict = {}  # message_id -> expira_en

    def _evict_expired(self, now: float):
        expired = [mid for mid, expires_at in self._seen.items() if expires_at <= now]
        for mid in expired:
            del self._seen[mid]

    def is_duplicate(self, message_id: str, now: float) -> bool:
        self._evict_expired(now)
        return message_id in self._seen

    def mark_seen(self, message_id: str, now: float):
        self._seen[message_id] = now + self.window_s


def draw_redelivery_delay(rng: random.Random) -> float:
    """La mayoria de las redeliveries ocurren rapido (segundos). Rara
    vez (2%) ocurren mucho despues — un consumidor que estuvo caido
    por horas, un mensaje reprocesado desde una dead letter queue
    (ver [4-dead-letter-queue](../4-dead-letter-queue)) dias despues.
    """
    if rng.random() < 0.02:
        return rng.uniform(300.0, 86400.0)
    return rng.uniform(0.1, 5.0)
