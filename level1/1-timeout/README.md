# 1. Timeout

## Que es

Un **timeout** es el limite de tiempo que un cliente esta dispuesto a
esperar la respuesta de una dependencia (servicio, base de datos, API
externa) antes de abortar la llamada y seguir adelante.

Es el patron de resiliencia mas basico y suele ser el primer paso
antes de aplicar retries, circuit breakers o bulkheads: **sin timeout,
esos patrones no tienen forma de saber cuando algo esta "colgado"**.

## Por que importa

Sin timeout, una dependencia lenta o caida puede:

- Bloquear el hilo/conexion del llamador indefinidamente.
- Agotar el pool de conexiones o el thread-pool del servicio que llama.
- Propagar la lentitud hacia arriba en la cadena de llamadas
  (cascading failure): un servicio lento vuelve lentos a todos sus
  consumidores.

Con un timeout bien elegido, el llamador falla rapido (*fail fast*),
libera el recurso y puede aplicar una estrategia de recuperacion
(fallback, retry, valor cacheado, etc.).

## Estructura del ejemplo

- `server.py`: servicio HTTP simulado cuyo tiempo de respuesta se
  controla con el query param `delay` (segundos).
- `client_timeout.py`: llama al servicio con `urllib.request.urlopen`
  usando el parametro `timeout`, y compara dos escenarios:
  1. El servicio responde antes del timeout -> exito.
  2. El servicio tarda mas que el timeout -> se aborta la espera y se
     usa un valor de respaldo.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_timeout.py
```

Salida esperada (los tiempos pueden variar levemente):

```
Escenario 1: el servicio responde rapido (1s), timeout generoso (5s)
  -> exito en 1.01s: {"delay_simulated": 1.0, "status": "ok"}

Escenario 2: el servicio es lento (5s), timeout corto (1s)
  -> TIMEOUT tras 1.00s (timed out); se usa fallback

Sin timeout, el llamador habria esperado los 5s completos.
Con el timeout de 1s, fallamos rapido y nos recuperamos con el fallback.
```

Nota clave del escenario 2: el llamador corta la espera a ~1s en vez
de bloquearse los 5s completos que tarda el servicio en responder.

## Puntos clave

- **Todo I/O de red debe tener timeout explicito.** El valor por
  defecto de muchas librerias (incluido `urllib`) es esperar
  indefinidamente si no se especifica `timeout`.
- El timeout debe calibrarse contra el SLA esperado de la dependencia,
  no elegirse al azar: muy corto genera falsos negativos, muy largo no
  protege de nada.
- Un timeout por si solo no resuelve el problema: define **cuando**
  rendirse. Que hacer despues (fallback, retry con backoff, circuit
  breaker) son patrones complementarios que se ven en los siguientes
  niveles.
