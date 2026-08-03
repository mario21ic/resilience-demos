"""Feature flags: decidir si una funcionalidad esta activa via
CONFIGURACION, no via codigo desplegado. Esto separa dos cosas que
suelen confundirse: DESPLEGAR (llevar codigo nuevo a produccion) y
LANZAR (hacer que ese codigo sea visible/activo para los usuarios). Se
puede desplegar una funcionalidad completamente apagada, y encenderla
despues sin volver a desplegar nada.

Un "kill switch" es la aplicacion mas critica de esto: un apagador de
emergencia. Si una funcionalidad recien lanzada esta causando
problemas, mitigar el incidente es tan rapido como apagar un flag —
nada de esperar un pipeline de build, tests y deploy.
"""
import zlib

PIPELINE_STAGES = {
    "revertir el commit": 1.0,
    "build": 4.0,
    "tests de CI": 6.0,
    "deploy progresivo": 5.0,
}

KILL_SWITCH_STAGES = {
    "apagar el flag en el panel": 0.1,
    "propagacion a las instancias corriendo": 0.5,
}


def is_enabled(user_id: str, percentage: float, flag_name: str = "default") -> bool:
    """Decide si `user_id` ve la funcionalidad, segun un porcentaje de
    rollout. El bucket de cada usuario sale de un hash ESTABLE de su
    ID (no de un sorteo al azar en cada llamada) — asi el mismo
    usuario siempre cae del mismo lado, y subir el porcentaje nunca le
    saca la funcionalidad a alguien que ya la tenia.
    """
    bucket = zlib.crc32(f"{flag_name}:{user_id}".encode()) % 100
    return bucket < percentage
