"""Retry budget: un limite compartido a CUANTOS reintentos se permiten
en total, independiente de cuantos reintentos autorice la logica de
una sola llamada (ver 2-retry).

Implementado como un token bucket, siguiendo el mismo algoritmo que
usa gRPC para "retry throttling" (propuesta A6): un pool de creditos
que se gasta con cada reintento y se recarga de a poco con cada exito.
"""


class RetryBudget:
    """Pool compartido de "creditos de reintento" para todo un cliente
    (o un pool de conexiones a un mismo backend), no por request.

    - Cada reintento consume 1 token.
    - Cada llamada exitosa (que no fue en si misma un reintento) repone
      `token_ratio` tokens, acotado a `max_tokens`.
    - Solo se autoriza un reintento si el budget conserva mas de la
      mitad de su capacidad (`tokens > max_tokens / 2`). Ese margen
      evita que el budget se vacie del todo y deje de reponerse nunca:
      si se permitiera gastar hasta 0, una racha larga de fallas nunca
      podria recuperar tokens porque no habria exitos que la recarguen.
    """

    def __init__(self, max_tokens: float = 10.0, token_ratio: float = 0.1):
        self.max_tokens = max_tokens
        self.token_ratio = token_ratio
        self.tokens = max_tokens

    def allow_retry(self) -> bool:
        if self.tokens > self.max_tokens / 2:
            self.tokens -= 1
            return True
        return False

    def on_success(self):
        self.tokens = min(self.max_tokens, self.tokens + self.token_ratio)
