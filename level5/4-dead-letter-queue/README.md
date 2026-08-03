# Dead Letter Queue + reproceso y poison pills

## Que es

Un **poison pill** es un mensaje que falla de forma persistente — no
por un problema transitorio (para eso esta el
[retry](../../level1/2-retry)), sino porque algo en el mensaje mismo
esta mal: datos corruptos, un formato inesperado, un bug que ese
payload especifico dispara. En una cola FIFO, reintentarlo en el
mismo lugar bloquea a **todos** los mensajes buenos que llegaron
despues — nadie mas avanza hasta que el primero se resuelva, y si
nunca se resuelve, la cola queda parada para siempre.

Una **Dead Letter Queue (DLQ)** es la valvula de escape: tras un
numero maximo de intentos, el mensaje problematico se saca de la cola
principal y se archiva por separado (junto con el motivo del fallo)
para investigarlo con calma, sin seguir bloqueando al resto.

## La DLQ no es un tacho de basura

Sacar un mensaje de la cola principal no lo resuelve — solo lo aisla.
La DLQ deberia guardar suficiente contexto (el error, el payload, el
numero de intentos) para poder diagnosticar QUE broke, y los mensajes
deberian reprocesarse **despues** de arreglar la causa raiz, no antes.
Reintentar ciegamente algo que sigue en la DLQ porque nunca se
investigo por que fallo simplemente lo devuelve al mismo lugar.

## Estructura del ejemplo

- `dlq.py`: `simulate_without_dlq` (el problema), `simulate_with_dlq`
  (la solucion, con un limite de intentos antes de archivar) y
  `reprocess_dlq` (reintentar desde la DLQ, con y sin haber arreglado
  la causa raiz).
- `demo_dlq.py`: tres partes, sobre una cola de 20 mensajes buenos con
  uno envenenado insertado en el medio.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_dlq.py
```

Salida esperada:

```
Parte 1 (sin DLQ):  procesados 5/20 — los otros 15 quedan atascados detras
                    del mensaje envenenado, que consume 95 intentos sin exito.

Parte 2 (con DLQ):  procesados 20/20 — el envenenado se aisla tras 3
                    intentos, con el motivo del fallo guardado.

Parte 3 (reproceso):
  sin arreglar el bug: vuelve a la DLQ igual (intentos: 4)
  arreglando el bug:   se procesa con exito
```

## Puntos clave

- Sin DLQ, un solo mensaje malo puede parar una cola entera — el
  radio de impacto de un bug de datos se vuelve "todo lo que viene
  despues", no solo el mensaje afectado.
- El limite de intentos antes de archivar tiene que ser mayor al de
  fallas transitorias normales (para no archivar algo que un simple
  retry hubiera resuelto) pero finito (para no bloquear la cola
  indefinidamente) — es el mismo tipo de balance que el umbral de un
  [circuit breaker](../../level2/1-circuit-breaker).
- Reprocesar la DLQ automaticamente y sin cambios es, en el mejor
  caso, inutil (vuelve al mismo lugar) y en el peor, peligroso (si el
  "arreglo" fue solo reintentar mas veces, sin entender por que
  fallaba).
- Esto se complementa con
  [consumidor idempotente](../3-consumidor-idempotente-dedup): un
  mensaje reprocesado desde la DLQ, posiblemente mucho despues de su
  primer intento, es exactamente el tipo de redelivery tardia que una
  ventana de deduplicacion corta puede no atrapar — la razon por la
  que ese ejemplo menciona la DLQ como fuente de redeliveries fuera de
  ventana.
