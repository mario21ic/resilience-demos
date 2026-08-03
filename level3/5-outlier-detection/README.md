# Outlier detection / ejection

## Que es

Un health check activo ([level3/3-health-check](../3-health-check)) le
pregunta explicitamente a cada replica "¿estas sana?". El **outlier
detection** hace algo distinto: observa los resultados **reales** del
trafico que ya se le esta mandando a cada replica, y saca del pool
—de forma automatica— a la que se comporta peor que sus pares. Es
health checking **pasivo**: no hace falta un endpoint dedicado, y
reacciona tan rapido como llegan los propios requests, en vez de
esperar al siguiente ciclo de probes.

Es exactamente el mecanismo que implementa Envoy con su "outlier
detection", y el mismo espiritu de otros balanceadores de produccion:
pasivo, basado en trafico real, y pensado como **complemento** de los
health checks activos, no como reemplazo — un activo puede tardar en
notar algo que ya se esta viendo en cada request real; un pasivo
necesita que haya trafico fluyendo para poder notar algo.

## Dos formas de detectar un outlier

1. **Fallas consecutivas**: la mas simple. Una racha de N fallas
   SEGUIDAS dispara la ejeccion; una falla aislada no. La duracion de
   la ejeccion crece con cada vez que la misma replica vuelve a fallar
   apenas se la reincorpora (`base_ejection_time * veces_eyectada`,
   igual que Envoy) — evita que una replica que "flapea" entre y
   salga del pool sin parar.
2. **Tasa de exito (estadistica)**: compara la tasa de exito reciente
   de cada replica contra el promedio del resto del pool, y eyecta las
   que caen muy por debajo (mas de `stdev_factor` desviaciones
   estandar bajo la media). No necesita un umbral fijo definido a
   mano — se adapta a lo que sea "normal" para ESE pool en ESE
   momento.

## El enemigo de la version estadistica: eyectar a todo el mundo

Si un problema es **compartido** (una dependencia comun degradada, una
zona de disponibilidad con latencia alta), MUCHAS replicas van a lucir
mal al mismo tiempo — no porque cada una individualmente este rota,
sino porque comparten la causa. Eyectarlas a todas no arregla nada y
deja **menos capacidad** para atender el trafico que si sigue
llegando — en el caso extremo, eyectar el 100% del pool es
estrictamente peor que no hacer nada.

La red de seguridad es un limite explicito: nunca eyectar mas de
`max_ejection_fraction` del pool de una sola vez. Cuando una fraccion
grande del pool luce mal, el limite prioriza dejar **algo** de
capacidad funcionando por sobre "limpiar" agresivamente el pool.

## Estructura del ejemplo

- `outlier_detector.py`: `ConsecutiveFailureEjector` (fallas seguidas
  + backoff de ejeccion) y `SuccessRateOutlierDetector` (outlier
  estadistico + cap de ejeccion maxima).
- `demo_outlier_detection.py`: tres partes.
  1. Una replica "flapper" que falla en rachas repetidas — la
     duracion de la ejeccion crece cada vez; un blip aislado no
     dispara nada.
  2. Un pool de 10 replicas con una sola realmente enferma — se
     identifica y eyecta sin umbral fijo.
  3. Un pool con 6 de 10 replicas compartiendo un problema — sin cap
     se eyectarian 4; con el cap del 34%, se limita a 3.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_outlier_detection.py
```

Salida esperada (resumen):

```
Parte 1: ola 1 ejectada 5 ticks, ola 2 -> 10 ticks, ola 3 -> 15 ticks, ola 4 -> 20 ticks
         un blip aislado de 2 fallas: NO se ejecta

Parte 2: bad (64% de exito) <- EJECTADA; el resto (~97-98%) no

Parte 3: sin cap: 4/10 replicas eyectadas
         con cap del 34%: 3/10 replicas eyectadas
```

## Puntos clave

- Pasivo y activo se complementan: el pasivo reacciona rapido cuando
  hay trafico real fluyendo; el activo sigue funcionando cuando una
  replica no recibe trafico (por ejemplo, porque ya fue sacada del
  pool) y hace falta saber si ya se puede reincorporar.
- El backoff de ejeccion es lo que evita que una replica inestable
  "flapee" dentro y fuera del pool sin parar — cada recaida cuesta
  mas tiempo afuera.
- La deteccion estadistica evita tener que elegir a mano un umbral de
  "tasa de exito aceptable" para cada servicio — compara cada replica
  contra sus pares, que es la señal que realmente importa.
- El cap de ejeccion maxima es la diferencia entre un mecanismo de
  proteccion y uno que puede convertirse en su propio incidente: sin
  el, un problema compartido puede hacer que el propio outlier
  detection deje el sistema sin ninguna capacidad.
- Esto se combina naturalmente con
  [load balancing](../4-load-balancing): el outlier detection decide
  QUE replicas estan en el pool; el balanceador (round robin,
  least-connections, P2C...) decide COMO repartir trafico entre las
  que quedan.
