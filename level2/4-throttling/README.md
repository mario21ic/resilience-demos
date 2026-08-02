# 4. Throttling

## Que es

El [rate limiting](../3-rate-limiting) protege al servidor
**rechazando** de inmediato lo que supera el limite. El **throttling**
persigue el mismo objetivo — no dejar que la demanda supere la
capacidad sostenible — pero con otra herramienta: en vez de rechazar,
**encola y demora** el exceso, procesandolo a un ritmo constante.

La diferencia le importa a quien hace el request: uno que recibe un
rechazo tiene que decidir que hacer (reintentar, mostrar un error,
usar un [fallback](../../level1/8-fallback)). Uno que recibe una
respuesta exitosa, aunque tarde un poco mas de lo normal, no tiene que
hacer nada distinto. El throttling cambia **latencia por
disponibilidad**; el rate limiting cambia una fraccion de los
requests por **proteccion inmediata**.

Ninguna cola puede ser infinita, asi que el throttling tambien
termina rechazando — pero solo cuando la espera resultante ya no es
razonable, no ante la primera rafaga que supera la capacidad
instantanea.

## El algoritmo: leaky bucket como cola

Se modela como una cola FIFO con tiempo de servicio fijo
(`1/rate` segundos por request):

- Cada request nuevo se agenda para el primer momento libre del
  "servidor" (`max(ahora, ultimo_turno_agendado)`).
- Si ese momento cae mas alla de lo que la cola puede absorber
  (`max_queue_size / rate`), se rechaza. Un request rechazado no le
  quita turno a nadie: la cola solo avanza con los que se aceptan.

Es el mismo "leaky bucket" del que a veces se habla en rate limiting,
pero usado como cola con demora en vez de como contador que solo
acepta o rechaza.

## Estructura del ejemplo

- `leaky_bucket.py`: `LeakyBucketThrottle.schedule(now)` devuelve el
  instante en que un request sera atendido, o lanza `QueueFullError`
  si la cola ya esta al limite.
- `server.py`: endpoint `GET /api/resource` que agenda cada request en
  la cola; si hay lugar, espera lo que le corresponda y responde
  `200`; si la cola esta llena, responde `503` de inmediato.
- `client_throttling.py`: dos partes.
  1. Compara, request a request, un rechazo inmediato (mismo concepto
     que el token bucket de rate limiting) contra el leaky bucket,
     sobre la misma rafaga de 10 requests simultaneos.
  2. La misma comparacion contra el endpoint HTTP real, midiendo la
     latencia que efectivamente ve el cliente en una rafaga
     concurrente.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_throttling.py
```

Salida esperada de la Parte 1 (deterministica; tasa=5/s, capacidad/cola=5):

```
 request |   rate limiter (rechazo inmediato) |        throttle (leaky bucket)
       1 |              aceptado (sin espera) |         aceptado, espera 0.00s
       5 |              aceptado (sin espera) |         aceptado, espera 0.80s
       6 |                          RECHAZADO |         aceptado, espera 1.00s
       7 |                          RECHAZADO |         RECHAZADO (cola llena)

Total aceptado -> rate limiter: 5/10, throttle: 6/10
```

El leaky bucket acepta un request mas en total (el 6to) convirtiendo
lo que hubiera sido un rechazo en una espera de 1 segundo — y solo
rechaza a partir de que la espera ya no es razonable.

La Parte 2 (HTTP real, ejecucion concurrente) muestra el mismo patron
sobre la red: la mayoria de los requests devuelve `200` con una
latencia que crece con la posicion en la cola (hasta ~1s), y los que
exceden la capacidad de la cola reciben `503` casi de inmediato, sin
esperar nada. Los tiempos exactos y el orden de llegada pueden variar
levemente por el scheduling real de los threads.

## Puntos clave

- Throttling y rate limiting no son excluyentes: muchos sistemas usan
  throttling para absorber rafagas cortas y caen a un rechazo tipo
  rate limiting cuando la sobrecarga es sostenida (la cola se
  mantiene llena).
- Una cola de throttling **debe** tener un limite (`max_queue_size`):
  sin uno, una rafaga sostenida generaria una espera creciente sin
  techo, que en la practica es peor que un rechazo rapido y claro.
- El throttling es una buena opcion cuando el llamador puede tolerar
  latencia extra (un job en background, un endpoint sin usuario
  esperando en pantalla); para trafico interactivo con expectativas
  de latencia estrictas, un rechazo temprano con
  [fallback](../../level1/8-fallback) puede ser mejor experiencia que
  una espera silenciosa.
- Este patron tambien aplica del lado del **cliente**: un cliente
  puede autolimitar el ritmo al que envia requests (en vez de
  mandarlos todos de una y dejar que el servidor decida) para no
  depender de que el servidor lo rechace — es la misma logica de
  leaky bucket, aplicada antes de salir a la red en vez de al llegar.
