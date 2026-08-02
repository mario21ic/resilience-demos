# 7. Request coalescing / single-flight

## Que es

Cuando una clave popular expira de un cache (o nunca estuvo), es comun
que muchos requests concurrentes intenten recalcularla o refetchearla
al mismo tiempo — un **cache stampede** (tambien llamado
*dog-piling*). Sin coordinacion, cada uno de esos requests dispara su
propia llamada identica al backend, multiplicando por N un trabajo
que solo hacia falta hacer una vez.

**Request coalescing** (tambien llamado **single-flight**) resuelve
esto del lado del cliente, o de una capa intermedia como un
cache-aside layer o un API gateway: el primer caller para una clave
ejecuta la llamada real; el resto de los callers concurrentes para esa
**misma clave** esperan y reciben el mismo resultado, sin generar
ninguna llamada adicional al backend.

Es el mismo patron que implementa `golang.org/x/sync/singleflight` en
Go, y que usan de forma equivalente varios clientes de cache (ej.
groupcache) para evitar que un backend reciba N copias identicas del
mismo trabajo caro en el mismo instante.

## Como funciona

1. Un caller pide `group.do(key, func)`.
2. Si nadie mas esta pidiendo esa `key` en este momento, este caller
   se vuelve el **lider**: ejecuta `func()` de verdad.
3. Si YA hay una llamada en curso para esa `key`, el caller se vuelve
   un **seguidor**: espera a que el lider termine, y recibe exactamente
   el mismo resultado (o la misma excepcion) que el.
4. Una vez que el lider termina, la entrada para esa `key` se libera:
   el proximo caller que la pida (ya sin nadie en curso) se convierte
   en el lider de una nueva llamada real.

## Estructura del ejemplo

- `single_flight.py`: `SingleFlightGroup.do(key, func, *args, **kwargs)`,
  con un lock protegiendo el diccionario de llamadas en curso y un
  `threading.Event` por clave para que los seguidores esperen al
  lider.
- `server.py`: backend "caro" simulado — cada invocacion real tarda
  0.3s y se cuenta en un contador global (`GET /debug/call_count`),
  para poder verificar cuantas veces se ejecuto DE VERDAD el trabajo.
- `client_request_coalescing.py`: tres partes, todas con rafagas de
  requests concurrentes (via threads) contra el mismo backend:
  1. 20 requests concurrentes por la misma clave, **sin** coalescing.
  2. Los mismos 20, **con** un `SingleFlightGroup`.
  3. Coalescing con dos claves distintas mezcladas (15 + 5), para
     confirmar que la deduplicacion es por clave, no global.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_request_coalescing.py
```

Salida esperada:

```
Parte 1: 20 requests concurrentes por la MISMA clave, SIN coalescing
  llamadas reales al backend: 20 (una por cada request concurrente)

Parte 2: los mismos 20 requests concurrentes, CON single-flight
  llamadas reales al backend: 1 (una sola, compartida por los 20)
  valores distintos de 'computed_at_call' recibidos: {1} (todos comparten la misma respuesta)

Parte 3: coalescing con DOS claves distintas mezcladas (15 + 5 concurrentes)
  llamadas reales al backend: 2 (una por CADA clave distinta, no una sola global)
```

Sin coalescing, 20 requests concurrentes generan 20 llamadas reales.
Con coalescing, generan **una sola**, y los 20 callers reciben
literalmente la misma respuesta (mismo `computed_at_call`) — no 20
respuestas iguales por coincidencia, sino la misma llamada compartida.

## Puntos clave

- Request coalescing solo tiene sentido para llamadas **idempotentes
  y cacheables dentro de la ventana de coalescing** (lecturas,
  calculos deterministas) — coalescer una escritura haria que varios
  callers distintos reciban el resultado de una operacion que
  solo uno de ellos pidio en realidad.
- No reemplaza a un cache: lo complementa. El cache evita trabajo
  repetido A LO LARGO DEL TIEMPO; el single-flight evita trabajo
  repetido EN EL MISMO INSTANTE, mientras el cache todavia no tiene
  (o ya no tiene) el valor.
- La deduplicacion es por clave: dos requests concurrentes por claves
  distintas nunca se bloquean entre si, cada una dispara su propio
  lider (ver Parte 3).
- Se combina naturalmente con el resto de level2: el single-flight
  reduce cuantas llamadas concurrentes llegan a golpear a una
  dependencia, lo cual reduce la presion sobre el
  [bulkhead](../2-bulkhead) o el
  [rate limit](../3-rate-limiting) del lado del backend, y baja la
  probabilidad de que una rafaga dispare el
  [circuit breaker](../1-circuit-breaker) por su cuenta.
