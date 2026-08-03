# Hedged requests

## Que es

Del paper ["The Tail at Scale"](https://research.google/pubs/pub40801/)
(Dean & Barroso, 2013): si una llamada no respondio dentro de un
umbral, se dispara una **copia** ("hedge") a otra replica, y se toma
la que responda primero. La otra se descarta (o se cancela, si el
protocolo lo permite).

Es distinto de un retry clasico ([level1/2-retry](../../level1/2-retry)):
un retry espera a que la llamada original **falle** antes de
reintentar; un hedge dispara la copia mientras la original **sigue en
curso**, apostando a que otra replica probablemente responda mas
rapido. No hace falta que la primera haya fallado — puede terminar
respondiendo igual, solo que tarde.

## El problema: la cola larga

Un servicio individual puede tener un p50 excelente y un p999
pesimo — un modo lento ocasional (una pausa de GC, contencion de
disco, ruido de un vecino en el mismo host) que casi nunca ocurre,
pero cuando ocurre, es varias veces mas lento que lo normal. Con
suficientes llamadas (o si un solo request agrega resultados de
cientos de replicas, como una busqueda), la probabilidad de que **al
menos una** caiga en ese modo lento se vuelve alta, aunque cada
replica individual rara vez lo sufra.

## La idea: una segunda oportunidad, independiente

Si el modo lento de cada replica es mayormente independiente del de
las demas, la probabilidad de que **dos** llamadas caigan en el modo
lento AL MISMO TIEMPO es mucho menor que la de que una sola lo haga.
Hedging aprovecha eso: en vez de esperar pasivamente a que la llamada
lenta termine, dispara una segunda oportunidad independiente apenas
se sospecha que la primera va lenta.

## Estructura del ejemplo

- `hedging.py`: `draw_latency` simula una replica con 5% de
  probabilidad de un stall lento por llamada; `hedged_call` implementa
  el mecanismo de hedge-tras-umbral.
- `demo_hedged_requests.py`: tres partes.
  1. La cola larga sin hedging: p50/p95/p99/p999 de 100.000 requests.
  2. Hedging con el umbral en el p95 observado: cuanto baja la cola,
     y cuanta carga extra genera.
  3. El tradeoff completo: barrido de umbrales desde p50 hasta p99,
     mostrando que mejorar la cola siempre cuesta mas carga — no hay
     un punto "optimo" universal.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_hedged_requests.py
```

Salida esperada (semilla fija):

```
Parte 1 (sin hedging):    p50=10.1ms  p95=100.7ms  p99=258.3ms  p999=296.0ms

Parte 2 (hedge en p95, umbral=100.7ms):
                sin hedging   con hedging
  p99:             258.3ms       112.6ms
  p999:            296.0ms       208.4ms
  carga extra: 5.0%

Parte 3 (barrido de umbrales):
  p50 -> carga extra 49.9%, p99=22.2ms, p999=177.6ms
  p95 -> carga extra  5.0%, p99=112.6ms, p999=208.4ms
  p99 -> carga extra  1.0%, p99=258.4ms, p999=270.8ms
```

## Puntos clave

- Hedging no mejora el caso comun (el p50 queda igual) — su valor
  esta enteramente en la cola. No tiene sentido hedgear si a nadie le
  importa el p99.
- El umbral es una perilla de negocio, no un valor tecnico fijo:
  umbrales bajos dan la mejor cola posible pero casi duplican la
  carga; umbrales altos casi no cuestan nada pero tampoco ayudan
  mucho, porque para cuando se disparan ya se pago casi todo el
  costo del stall.
- El beneficio depende de que los modos lentos de las replicas sean
  mayormente **independientes** entre si — si comparten una causa
  comun (la misma degradacion de red, el mismo problema de
  infraestructura subyacente), hedgear no ayuda: ambas copias van a
  ser lentas por la misma razon.
- Hedging genera trabajo REDUNDANTE a proposito — para que valga la
  pena, la operacion hedgeada tiene que ser barata de duplicar
  (idempotente, sin efectos secundarios costosos) y el sistema
  necesita tener margen de capacidad de sobra para absorber esa carga
  extra sin degradarse el mismo.
- Esto se conecta directo con
  [multiplexing + connection pooling](../../level3/6-multiplexer):
  hedging solo es barato de disparar si la conexion al backup ya esta
  caliente — sin eso, el costo de abrir la conexion del hedge puede
  comerse buena parte de la ganancia.
