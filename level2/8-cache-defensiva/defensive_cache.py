"""Tres tecnicas de cacheo defensivo, cada una resolviendo un problema
distinto de un cache "ingenuo" (guardar valor + TTL, recalcular al
vencer):

  - SWRCache: al vencer, sirve el valor VIEJO de inmediato en vez de
    bloquear al llamador, mientras refresca en background.
  - CacheWithNegativeEntries: cachea tambien los "no existe", con un
    TTL mas corto que las entradas positivas.
  - should_refresh_early: decide, probabilisticamente, refrescar un
    poco ANTES del vencimiento real, para que distintos lectores no
    lo detecten todos en el mismo instante exacto.
"""
import math
import random
import threading
import time


# --- Stale-while-revalidate ------------------------------------------------


class SWRCache:
    """Cache con stale-while-revalidate: al vencer el TTL "fresco", en
    vez de bloquear a quien pide el valor mientras se refresca, se le
    devuelve el valor VIEJO de inmediato y se dispara un refresco en
    background (uno solo a la vez, sin importar cuantos lectores
    encuentren el valor stale al mismo tiempo).

    Solo se bloquea si todavia no hay ningun valor en cache, o si el
    valor ya paso incluso la ventana de "viejo pero utilizable"
    (`ttl + stale_ttl`).
    """

    def __init__(self, ttl: float, stale_ttl: float):
        self.ttl = ttl
        self.stale_ttl = stale_ttl
        self._lock = threading.Lock()
        self._value = None
        self._fetched_at = None
        self._refreshing = False

    def get(self, fetch_fn):
        now = time.monotonic()

        with self._lock:
            has_value = self._fetched_at is not None
            age = now - self._fetched_at if has_value else None
            is_fresh = has_value and age <= self.ttl
            is_stale_but_usable = has_value and self.ttl < age <= self.ttl + self.stale_ttl

            if is_fresh:
                return self._value, "fresh"

            stale_value = self._value
            start_refresh = False
            if is_stale_but_usable and not self._refreshing:
                self._refreshing = True
                start_refresh = True

        if is_stale_but_usable:
            if start_refresh:
                threading.Thread(target=self._refresh_in_background, args=(fetch_fn,), daemon=True).start()
            return stale_value, "stale (refresh en background)"

        return self._blocking_fetch(fetch_fn), "miss (fetch sincronico)"

    def _refresh_in_background(self, fetch_fn):
        try:
            value = fetch_fn()
            with self._lock:
                self._value = value
                self._fetched_at = time.monotonic()
        finally:
            with self._lock:
                self._refreshing = False

    def _blocking_fetch(self, fetch_fn):
        value = fetch_fn()
        with self._lock:
            self._value = value
            self._fetched_at = time.monotonic()
        return value


# --- Negative caching -------------------------------------------------------


class CacheWithNegativeEntries:
    """Cache que distingue entradas positivas (TTL largo) de entradas
    negativas — "esto no existe" — con un TTL mas corto, para no
    seguir golpeando al backend por algo que ya sabemos que no existe,
    sin arriesgarse a creer eso para siempre si el dato aparece
    despues.
    """

    MISSING = object()  # sentinel para "el backend confirmo que no existe"

    def __init__(self, positive_ttl: float, negative_ttl: float):
        self.positive_ttl = positive_ttl
        self.negative_ttl = negative_ttl
        self._entries: dict[str, tuple[object, float]] = {}

    def get_or_fetch(self, key: str, fetch_fn):
        now = time.monotonic()

        entry = self._entries.get(key)
        if entry is not None:
            value, expires_at = entry
            if now < expires_at:
                return value  # sirve del cache, sea positivo o MISSING

        value = fetch_fn(key)
        ttl = self.negative_ttl if value is self.MISSING else self.positive_ttl
        self._entries[key] = (value, now + ttl)
        return value


# --- Expiracion probabilistica temprana (XFetch) ----------------------------


def should_refresh_early(now: float, expires_at: float, delta: float, beta: float = 1.0) -> bool:
    """Formula de XFetch ("Optimal Probabilistic Cache Stampede
    Prevention", Vattani et al.): a medida que se acerca el
    vencimiento, la probabilidad de disparar un refresco anticipado
    crece suavemente, en vez de que todos los lectores concurrentes lo
    detecten exactamente en el mismo instante del vencimiento real.

    `delta` es cuanto costo (en segundos) la ultima recomputacion:
    cuanto mas cara es de recalcular, con mas anticipacion conviene
    empezar a intentarlo. `beta` es una perilla para ajustar que tan
    agresivo es el refresco anticipado (1.0 = el valor del paper).

    Garantiza dispararse siempre en `now >= expires_at`, sin importar
    el sorteo aleatorio (en ese punto la formula se vuelve verdadera
    para cualquier resultado de `random()` en (0, 1)).
    """
    return now - delta * beta * math.log(random.random()) >= expires_at
