# 6. Retry budget

## Que es

El retry de [2-retry](../2-retry) decide, **para una sola llamada**,
cuantas veces reintentar. Eso resuelve el caso de una falla puntual,
pero no protege al backend cuando el que esta degradado es el
backend completo: si de golpe fallan el 90% de las llamadas, "cada
llamada reintenta una vez" implica que la carga total contra ese
backend casi se **duplica**, justo en el peor momento para hacerlo.

Un **retry budget** ataca el problema desde otro angulo: un limite
**compartido** a cuantos reintentos se permiten en total — por
cliente, por servicio, o por pool de conexiones — sin importar
cuantos reintentos autorizaria la logica de cada request individual.
Cuando el budget se agota, las llamadas que fallan devuelven el error
de inmediato (fail fast) en lugar de reintentar.

Es el mismo espiritu que un [circuit breaker](../), pero mas fino:
en vez de cortar TODO el trafico hacia un backend, solo recorta la
porcion que corresponde a reintentos — el trafico "extra" que el
cliente elige generar por su cuenta, no el trafico organico.

## El algoritmo: token bucket (igual al retry throttling de gRPC)

Este ejemplo implementa el mismo mecanismo que usa gRPC para
"retry throttling" (propuesta [A6](https://github.com/grpc/proposal)):

- Un pool empieza con `max_tokens` creditos (ej. 10).
- Cada reintento consume 1 token.
- Cada llamada exitosa que **no** fue en si misma un reintento repone
  `token_ratio` tokens (ej. 0.1), acotado a `max_tokens`.
- Un reintento solo se autoriza si el pool conserva **mas de la
  mitad** de su capacidad (`tokens > max_tokens / 2`).

Ese margen del 50% es intencional: si se permitiera gastar el pool
hasta 0, una racha larga de fallas dejaria el budget en un estado del
que nunca podria recuperarse (no habria margen para que un exito
aislado lo reponga antes de que otra falla lo vuelva a vaciar).

## Estructura del ejemplo

- `retry_budget.py`: la clase `RetryBudget` (`allow_retry()`,
  `on_success()`), documentada con el porque del umbral del 50%.
- `demo_retry_budget.py`: simula 500 llamadas en tres fases —
  **sano** (5% de fallas), **outage** (95% de fallas) y
  **recuperacion** (vuelve a 5%) — y compara, con la misma secuencia
  exacta de exitos/fallas:
  1. Retry sin budget: siempre reintenta una vez si la llamada falla.
  2. Retry con budget: solo reintenta si el `RetryBudget` lo autoriza.

Usar la misma secuencia de resultados en ambas simulaciones aisla el
efecto del budget: la diferencia en los numeros es 100% atribuible al
mecanismo, no a la suerte de una corrida aleatoria distinta.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_retry_budget.py
```

Salida esperada (semilla fija, `7`):

```
          fase | requests | retries sin budget | retries con budget | denegados | tokens al final
sano           |      200 |                 11 |                 11 |         0 |            10.0
outage         |      100 |                 94 |                  6 |        88 |             4.7
recuperacion   |      200 |                 12 |                 12 |         0 |            10.0

Llamadas totales al backend  sin budget: 617
Llamadas totales al backend  con budget: 529
Reduccion de carga con budget: 14.3%

Tasa de exito global sin budget: 411/500 (82.2%)
Tasa de exito global con budget: 407/500 (81.4%)
```

Durante el outage, sin budget se generan 94 reintentos (casi tantos
como requests originales); con budget, apenas 6 antes de que el pool
caiga por debajo del umbral y el resto (88) se deniegue. La tasa de
exito global casi no se resiente, porque esos reintentos denegados
casi nunca iban a tener exito de todas formas.

## Puntos clave

- El retry budget es un limite **de flota**, no de una sola llamada:
  complementa (no reemplaza) el `max_attempts` + backoff + jitter de
  una request individual.
- Cuando el backend esta ampliamente degradado, la mayoria de los
  reintentos "extra" fallan igual — denegarlos protege al backend con
  un costo casi nulo en tasa de exito real.
- El budget se recupera solo, de a poco, con cada exito: no hace
  falta un mecanismo separado de "medio abierto" como en un circuit
  breaker clasico, aunque ambos patrones pueden convivir.
- Es especialmente valioso en sistemas con muchos clientes
  independientes: sin un limite compartido, cada cliente reintentando
  "razonablemente" por su cuenta puede sumar, en conjunto, una carga
  nada razonable sobre el backend.
