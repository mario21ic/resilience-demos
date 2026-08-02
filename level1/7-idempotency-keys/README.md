# 7. Idempotency keys

## Que es

El retry ([2-retry](../2-retry)) asume que reintentar una llamada
fallida es seguro. Eso es cierto para operaciones **idempotentes**
(un `GET`, un "fijar el valor de X a 5" — repetirlas no cambia el
resultado), pero **no** para operaciones con efectos secundarios como
"cobrar una tarjeta" o "crear un pedido".

El problema de fondo es que un timeout del lado del cliente no dice
nada sobre que paso del lado del servidor. Cuando el cliente no
recibe respuesta a tiempo, hay dos posibilidades indistinguibles para
el:

1. El request nunca llego a procesarse -> reintentar es seguro.
2. El request **si se proceso**, pero la respuesta se perdio en el
   camino (o llego tarde) -> reintentar duplicaria el efecto.

Una **idempotency key** resuelve esta ambiguedad: el cliente genera
una clave unica por **operacion logica** (no por intento de red, ni
por request HTTP) y la reenvia igual en cada intento y cada retry. El
servidor recuerda que claves ya proceso; si ve una que ya conoce,
devuelve el resultado guardado en vez de repetir el efecto.

## Estructura del ejemplo

- `server.py`: servicio HTTP simulado con `POST /charge`, que tiene un
  efecto real (incrementa un contador de "cobros procesados"). Lee el
  header `Idempotency-Key` (la convencion que usan Stripe y varias
  APIs de pagos):
  - Si la key ya fue procesada antes, devuelve la respuesta guardada
    con `"replayed": true`, **sin** volver a ejecutar el efecto.
  - Si es nueva, procesa el cobro, lo guarda asociado a esa key, y
    responde con `"replayed": false`.
  - Con `simulate_lost_response=1`, el servidor demora la respuesta a
    proposito **despues** de ya haber procesado el cobro — simulando
    que la respuesta se pierde aunque el efecto ya ocurrio.
- `client_idempotency.py`: compara dos escenarios contra el mismo
  servicio, con el mismo timeout corto del lado del cliente:
  1. **Sin idempotency key**: el retry no tiene forma de decirle al
     servidor "esto ya lo intente antes" -> el cobro se duplica.
  2. **Con idempotency key**: el cliente genera una clave al iniciar
     la operacion y la reutiliza en el retry -> el servidor detecta
     el duplicado y responde con el resultado ya calculado.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_idempotency.py
```

Salida esperada:

```
Escenario A: retry SIN reutilizar idempotency key
  intento 1: TIMEOUT en el cliente (el servidor SI llego a procesar el cobro)
  intento 2 (retry): -> respuesta: {'charge_id': 'ch_2', 'amount': '100', 'replayed': False}
  cobros reales procesados por el servidor: 2 (se cobro DOS veces por una sola compra)

Escenario B: retry reutilizando la MISMA idempotency key
  intento 1: TIMEOUT en el cliente (el servidor SI llego a procesar el cobro)
  intento 2 (retry): -> respuesta: {'charge_id': 'ch_1', 'amount': '100', 'replayed': True}
  cobros reales procesados por el servidor: 1 (una sola vez, el retry solo repitio la respuesta)
```

El escenario A genera `ch_1` (que el cliente nunca llega a ver por el
timeout) y luego `ch_2` en el retry: dos cobros reales por una sola
compra. El escenario B genera `ch_1` una sola vez; el retry recibe
exactamente esa misma respuesta marcada como `replayed`.

## Puntos clave

- La idempotency key la genera el **cliente**, al iniciar la
  operacion logica — no en cada intento de red. Debe ser la misma en
  el request original y en todos sus reintentos.
- Un UUID por operacion (no por sesion, no por usuario, no
  reutilizado entre compras distintas) es la practica estandar.
- El servidor necesita guardar el resultado asociado a cada key el
  tiempo suficiente para cubrir la ventana realista de reintentos
  (ej. Stripe conserva las keys 24 horas), y suele exponer eso como
  parte del contrato de su API.
- Este patron es lo que hace **seguro** combinar retry + timeout
  ([1-timeout](../1-timeout), [2-retry](../2-retry)) incluso sobre
  operaciones que no son naturalmente idempotentes: la idempotencia
  se la agrega el protocolo, no la operacion en si.
- Sin idempotency keys, la alternativa es no reintentar nunca
  operaciones con efectos secundarios, o aceptar el riesgo de
  duplicados — ninguna de las dos es satisfactoria en un sistema que
  necesita ser resiliente.
