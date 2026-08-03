"""Deteccion de fallas por health checks, y las dos formas de
reaccionar a lo que detectan: failover automatico o manual.

Un solo health check fallido no alcanza para declarar muerto a un
nodo — un jitter momentaneo de red generaria failovers todo el
tiempo. Se exige un numero de fallas CONSECUTIVAS (`fail_threshold`)
antes de considerar al nodo caido, y ese mismo mecanismo hace que un
check sano vuelva a considerarlo vivo de inmediato.
"""


class HealthChecker:
    def __init__(self, fail_threshold: int = 3):
        self.fail_threshold = fail_threshold
        self._consecutive_failures = 0
        self.considered_down = False

    def record(self, is_healthy: bool) -> bool:
        """Registra el resultado de un check. Devuelve True si el
        estado de "considerado caido" CAMBIO en este check.
        """
        was_down = self.considered_down
        if is_healthy:
            self._consecutive_failures = 0
            self.considered_down = False
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.fail_threshold:
                self.considered_down = True
        return was_down != self.considered_down


class AutomaticFailover:
    """Actua apenas el health checker considera caido al primario:
    dispara el failover en ese mismo tick, y la promocion tarda
    `promotion_delay` ticks adicionales en completarse. Una vez
    disparado, no da marcha atras aunque el health check se recupere
    despues (el failover ya esta en curso).
    """

    def __init__(self, promotion_delay: int):
        self.promotion_delay = promotion_delay
        self.triggered_at = None
        self.promoted_at = None

    def on_considered_down(self, t: int):
        if self.triggered_at is None:
            self.triggered_at = t
            self.promoted_at = t + self.promotion_delay

    def on_considered_up(self, t: int):
        pass


class ManualFailover:
    """Espera `confirm_delay` ticks de confirmacion humana antes de
    disparar. Si el health checker vuelve a ver al primario sano ANTES
    de que se cumpla esa espera, la confirmacion pendiente se cancela
    — nadie llega a promover nada. Es, sin querer, una defensa contra
    particiones de red que se resuelven solas antes de que un humano
    llegue a actuar.
    """

    def __init__(self, confirm_delay: int, promotion_delay: int):
        self.confirm_delay = confirm_delay
        self.promotion_delay = promotion_delay
        self._pending_since = None
        self.triggered_at = None
        self.promoted_at = None

    def on_considered_down(self, t: int):
        if self.triggered_at is not None:
            return
        if self._pending_since is None:
            self._pending_since = t
        elif t - self._pending_since >= self.confirm_delay:
            self.triggered_at = t
            self.promoted_at = t + self.promotion_delay

    def on_considered_up(self, t: int):
        if self.triggered_at is None:
            self._pending_since = None
