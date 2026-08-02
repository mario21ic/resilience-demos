# 2. Retry

## Que es

**Retry** consiste en reintentar automaticamente una operacion que
fallo, bajo la suposicion de que la falla es **transitoria** (un
timeout puntual, un pico de carga, una caida momentanea de red o de
una instancia detras de un load balancer).

Se apoya en el patron de [timeout](../1-timeout) visto antes: cada
intento individual debe tener su propio limite de tiempo, si no, un
retry puede terminar esperando indefinidamente en cada intento.

## Por que importa (y por que hacerlo mal es peligroso)

Reintentar bien puede convertir una falla visible para el usuario en
algo completamente transparente. Pero reintentar **sin cuidado**
puede empeorar un incidente:

- **Retry storm**: si el servicio esta degradado por sobrecarga y
  todos los clientes reintentan de inmediato, la carga extra puede
  impedir que se recupere (o directamente tumbarlo).
- **Amplificacion**: un solo request de usuario puede convertirse en
  varios requests reales al backend, multiplicando la carga en
  cascada si hay varios niveles de servicios reintentando entre si.
- **Reintentar algo no idempotente** (ej. "cobrar una tarjeta",
  "crear un pedido") puede duplicar efectos secundarios si el primer
  intento en realidad si se proceso pero la respuesta se perdio.

## La mitigacion: backoff exponencial + jitter + limite de intentos

- **Backoff exponencial**: la espera entre intentos crece
  (`base * 2^intento`), dando tiempo a que el servicio se recupere en
  vez de insistir al mismo ritmo.
- **Jitter**: se le agrega aleatoriedad a la espera para que muchos
  clientes fallando al mismo tiempo no reintenten todos en el mismo
  instante (eso seria, de nuevo, un retry storm sincronizado).
- **Max attempts**: un tope de reintentos para no quedar reintentando
  para siempre; al agotarse, se recurre a un fallback, una cola para
  reintento diferido, o se propaga el error.
- **Reintentar solo errores retryable**: fallas transitorias (timeouts,
  5xx, errores de conexion), nunca errores 4xx de cliente (ej. 400,
  404, 422) que van a fallar siempre igual sin importar cuantas veces
  se reintenten.

## Estructura del ejemplo

- `server.py`: servicio HTTP simulado (`/flaky`) que falla con `503`
  las primeras `fail_times` veces para una `key` dada, y luego
  responde `200`. Tambien expone `/reset` para reiniciar el contador
  de una `key` entre escenarios.
- `client_retry.py`: compara tres escenarios contra ese servicio:
  1. `retry_naive`: reintenta de inmediato, sin espera (anti-patron).
  2. `retry_with_backoff`: backoff exponencial + jitter (recomendado).
  3. Una falla **permanente** que agota los `max_attempts` y termina
     lanzando `RetryExhausted`.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_retry.py
```

Salida esperada (los tiempos de espera varian por el jitter aleatorio):

```
Escenario 1: retry naive contra una falla transitoria (falla 2 veces, luego exito)
  intento 1: fallo (503), reintentando sin espera...
  intento 2: fallo (503), reintentando sin espera...
  intento 3: exito -> ok tras 3 intento(s)
  tiempo total: 0.00s

Escenario 2: retry con backoff exponencial + jitter, misma falla transitoria
  intento 1: fallo (503), esperando 0.08s antes de reintentar...
  intento 2: fallo (503), esperando 0.02s antes de reintentar...
  intento 3: exito -> ok tras 3 intento(s)
  tiempo total: 0.11s

Escenario 3: falla permanente (el servicio nunca se recupera) -> se agotan los reintentos
  intento 1: fallo (503), esperando 0.14s antes de reintentar...
  intento 2: fallo (503), esperando 0.16s antes de reintentar...
  intento 3: fallo (503), esperando 0.40s antes de reintentar...
  -> se agotaron 4 intentos; hay que usar un fallback o propagar el error al llamador
```

El escenario 1 "funciona" pero es el comportamiento que queremos
evitar en produccion: no da tiempo al servicio a recuperarse y, con
muchos clientes concurrentes, se convierte en un retry storm.

## Puntos clave

- Retry sin backoff+jitter no es gratis: bajo carga real puede
  empeorar el incidente que intenta resolver.
- Combina siempre retry con timeout por intento (patron anterior) y un
  limite maximo de intentos.
- Solo reintentes operaciones idempotentes o errores claramente
  transitorios; nunca reintentes ciegamente cualquier error.
- Cuando se agotan los reintentos, el llamador necesita un plan B
  (fallback, circuit breaker, cola de reintento diferido) — eso se ve
  en los siguientes niveles.
