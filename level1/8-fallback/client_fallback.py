"""Demo del patron de resiliencia: Fallback.

Timeout ([1-timeout](../1-timeout)) y retry ([2-retry](../2-retry))
responden "cuanto esperar" y "cuando reintentar". Pero en algun
momento hay que rendirse — y ahi entra el fallback: en vez de
propagarle el error al llamador, se le devuelve una respuesta
alternativa, aceptando que sea de peor calidad a cambio de que el
llamador nunca se quede sin nada que mostrar.

Este demo implementa una cadena de fallback de tres niveles, tipica
en sistemas de recomendaciones, catalogos, feature flags, etc.:

  1) Primario: llamar al servicio real, con timeout.
  2) Cache (stale-if-error): si el primario falla, usar la ULTIMA
     respuesta exitosa que se tenga guardada para ese usuario, aunque
     ya no sea fresca.
  3) Default estatico: si ni siquiera hay algo en cache, devolver un
     valor generico predefinido (ej. "mas vendidos").

Cada respuesta se marca con su `source` y un flag `degraded`, para que
quien la reciba sepa si esta viendo el dato real o una alternativa —
un fallback silencioso que no se distingue de la respuesta real es en
si mismo un riesgo (se puede tomar una decision de negocio sobre un
dato viejo sin saberlo).
"""
import json
import threading
import time
import urllib.error
import urllib.request

from server import start_server

HOST, PORT = "localhost", 8768
BASE_URL = f"http://{HOST}:{PORT}/"

_cache: dict[str, list[str]] = {}
_DEFAULT_ITEMS = ["mas vendidos", "mas vendidos #2", "mas vendidos #3"]


def set_backend_health(state: str):
    urllib.request.urlopen(f"{BASE_URL}admin/health?state={state}", timeout=2).read()


def call_primary(user_id: str, timeout_s: float) -> list[str]:
    url = f"{BASE_URL}recommendations?user_id={user_id}"
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read())["items"]


def get_recommendations(user_id: str, timeout_s: float = 1.0) -> dict:
    try:
        items = call_primary(user_id, timeout_s)
        _cache[user_id] = items  # se refresca la cache con cada respuesta fresca
        return {"user_id": user_id, "items": items, "source": "primario", "degraded": False}
    except (urllib.error.URLError, TimeoutError):
        pass

    if user_id in _cache:
        return {"user_id": user_id, "items": _cache[user_id], "source": "cache (stale)", "degraded": True}

    return {"user_id": user_id, "items": _DEFAULT_ITEMS, "source": "default estatico", "degraded": True}


def print_call(label: str, result: dict):
    marker = "DEGRADADO" if result["degraded"] else "OK"
    print(f"  {label:<28} [{marker:>9}] source={result['source']:<16} items={result['items']}")


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)  # da tiempo a que el servidor quede listo

    print("Fase 1: backend sano -> ambos usuarios reciben recomendaciones reales")
    set_backend_health("healthy")
    print_call("alice (primera vez)", get_recommendations("alice"))
    print_call("bob (primera vez)", get_recommendations("bob"))
    print("  (la cache queda poblada para alice y bob)\n")

    print("Fase 2: backend caido -> fallback en accion")
    set_backend_health("down")
    print_call("alice (tiene cache)", get_recommendations("alice"))
    print_call("bob (tiene cache)", get_recommendations("bob"))
    print_call("charlie (sin cache)", get_recommendations("charlie"))
    print()

    print("Fase 3: backend lento (supera el timeout del cliente) -> mismo fallback")
    set_backend_health("slow")
    print_call("alice (timeout, usa cache)", get_recommendations("alice", timeout_s=0.5))
    print()

    print("Fase 4: backend se recupera -> se vuelve a servir dato real y se refresca la cache")
    set_backend_health("healthy")
    print_call("alice (backend recuperado)", get_recommendations("alice"))
    print_call("charlie (backend recuperado)", get_recommendations("charlie"))

    server.shutdown()


if __name__ == "__main__":
    main()
