# 3. Rate limiting

## Que es

El [bulkhead](../2-bulkhead) limita cuanta capacidad del **cliente**
puede consumir una dependencia. El **rate limiting** resuelve el
problema simetrico del lado del **servidor**: cuantos requests por
segundo esta dispuesto a aceptar, sin importar quien los mande ni si
en ese instante puntual "tendria" capacidad de sobra.

Es un limite de **politica**, no una reaccion a que algo ya haya
fallado — a diferencia del [circuit breaker](../1-circuit-breaker),
que reacciona a una degradacion ya detectada, el rate limiting actua
preventivamente, siempre, este el backend sano o no.

## Parte 1: tres algoritmos, la misma linea de tiempo

No todos los rate limiters son iguales. Este ejemplo implementa los
tres mas comunes y los compara contra la misma secuencia de 20
requests (limite nominal: 10 req/s):

- **Fixed window**: cuenta requests en ventanas de reloj fijas
  (`[0,1)`, `[1,2)`, ...). Simple, pero tiene un defecto conocido: si
  el trafico se concentra justo en el borde entre dos ventanas, cada
  mitad se cuenta por separado y el limite efectivo se **duplica**.
- **Sliding window log**: guarda el timestamp de cada request
  aceptado y siempre mira los ultimos `window_size` segundos reales
  hacia atras, sin importar donde caigan los bordes del reloj.
- **Token bucket**: un balde de `capacity` tokens que se recarga
  continuamente a `rate` tokens/segundo; cada request consume uno.
  Permite absorber una rafaga corta (hasta `capacity` de una vez) sin
  dejar de limitar el promedio sostenido — el mismo algoritmo que usan
  AWS API Gateway y Stripe.

La linea de tiempo del demo tiene trafico normal, mas una rafaga de 10
requests justo **antes** del segundo 1.0 y otra de 10 justo
**despues**: exactamente la condicion que expone el defecto del fixed
window.

## Estructura del ejemplo

- `rate_limiters.py`: `FixedWindowLimiter`, `SlidingWindowLogLimiter`,
  `TokenBucketLimiter`, todos con la misma interfaz
  `allow_request(now) -> bool` — sin I/O, faciles de comparar.
- `server.py`: endpoint `GET /api/resource` protegido con un
  `TokenBucketLimiter` (capacidad=5, tasa=5/s), que responde
  `429 Too Many Requests` con el header `Retry-After` cuando se supera
  el limite.
- `client_rate_limiting.py`: dos partes.
  1. Corre la misma linea de tiempo contra los tres algoritmos y
     compara cuantos requests deja pasar cada uno.
  2. Golpea el endpoint HTTP real con una rafaga de 10 requests
     inmediatos, muestra los `429` con su `Retry-After`, espera ese
     tiempo, y reintenta.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_rate_limiting.py
```

Salida esperada de la Parte 1 (deterministica):

```
Fixed window:
  -> total permitido: 20/20 (de los cuales 15 son parte de la rafaga de 20 alrededor del borde)

Sliding window log:
  -> total permitido: 11/20 (de los cuales 6 son parte de la rafaga de 20 alrededor del borde)

Token bucket:
  -> total permitido: 16/20 (de los cuales 11 son parte de la rafaga de 20 alrededor del borde)
```

El fixed window deja pasar **el bloque entero de 20 requests** —el
doble del limite nominal de 10/s— porque cada rafaga de 10 cae en una
ventana de reloj distinta. Sliding window log es el mas estricto
(11/20): siempre mira los ultimos 1000ms reales, sin bordes que
explotar. Token bucket queda en el medio (16/20): esto no es un bug,
es su diseño — esta pensado para tolerar rafagas cortas hasta su
`capacity`, a cambio de no ser tan estricto como el sliding window en
un caso adversarial como este.

La Parte 2 (HTTP real) muestra el patron completo: los primeros 5
requests de una rafaga tienen exito (el balde arranca lleno), el resto
recibe `429` con un `Retry-After` cada vez mas preciso, y despues de
esperar ese tiempo el balde vuelve a tener tokens disponibles. Los
tiempos exactos pueden variar levemente por el reloj real.

## Puntos clave

- El fixed window es el mas simple de implementar pero el unico de
  los tres con un defecto explotable — evitarlo no es prematuro,
  es necesario en cuanto el trafico es adversarial o simplemente
  bursty.
- Sliding window log es el mas preciso, pero guarda un timestamp por
  request dentro de la ventana — mas costoso en memoria a alta escala
  (existen variantes "sliding window counter" que aproximan esto con
  menos estado).
- Token bucket es el mas usado en la practica porque su parametro de
  `capacity` es una perilla explicita para "cuanta rafaga tolero",
  separada de `rate` ("cual es el promedio sostenido que permito") —
  eso es una decision de producto, no solo una decision tecnica.
- El header `Retry-After` en la respuesta `429` es lo que conecta este
  patron con [retry](../../level1/2-retry) y
  [backoff](../../level1/3-backoff-exp) del lado del cliente: un buen
  cliente no debe reintentar a ciegas con su propio backoff, sino
  respetar lo que el servidor le esta diciendo explicitamente.
