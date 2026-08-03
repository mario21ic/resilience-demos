# Progressive delivery con auto-rollback por SLO

## Que es

Es el modelo de herramientas como Flagger o Argo Rollouts: durante un
rollout por oleadas, un analizador automatico mide metricas reales en
cada oleada contra los SLOs definidos, y si se violan, hace
**rollback completo** — no solo frena el avance, devuelve el trafico
a la version estable — sin que nadie tenga que estar mirando un
dashboard a las 3 de la manana.

Va un paso mas alla del criterio automatico simple de
[canary/blue-green/rolling](../1-canary-blue-green-rolling): en vez de
mirar una sola metrica una vez por oleada, mira **varias metricas** a
la vez (cualquiera puede disparar el rollback) y exige **varios
chequeos seguidos** fallando antes de actuar, para no reaccionar a
ruido estadistico normal.

## Por que una sola metrica no alcanza

Un canary puede tener la tasa de error perfecta y aun asi estar roto:
una regresion de performance (una query nueva sin indice, un
N+1 recien introducido) puede degradar la latencia sin generar ni un
solo error. Un gate que solo mira error rate lo deja pasar sin
problema — el gate tiene que mirar **todas** las señales que
importan, no solo la mas facil de medir.

## Por que un solo chequeo malo tampoco alcanza

Las metricas reales tienen ruido: un pico aislado de latencia en una
version perfectamente sana es normal, no un sintoma. Si el gate
reacciona al primer chequeo que sale mal, va a revertir deploys sanos
todo el tiempo por pura casualidad estadistica. Exigir varios
chequeos **consecutivos** fallando (no solo alguno, sino varios
seguidos) filtra el ruido sin dejar de reaccionar ante una
degradacion real y sostenida.

## Estructura del ejemplo

- `progressive_delivery.py`: `draw_metrics` (simula error rate y
  latencia, con o sin degradacion real, con o sin ruido normal) y
  `run_progressive_delivery` (el analizador: avanza oleada por
  oleada, hace rollback si se acumulan suficientes chequeos malos
  seguidos).
- `demo_progressive_delivery.py`: dos partes.
  1. Gate de una sola metrica vs multi-metrica, con un problema real
     de latencia (sin errores).
  2. Cuantos rollbacks innecesarios genera exigir 1 vs 3 chequeos
     consecutivos malos, sobre una version sana con ruido normal
     (2000 simulaciones).

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_progressive_delivery.py
```

Salida esperada:

```
Parte 1 (latencia degradada, error rate normal):
  gate solo error rate:      fully_promoted en 100%
  gate error rate + latencia: rolled_back en 10%

Parte 2 (version sana, con ruido — 2000 simulaciones):
  1 chequeo seguido exigido: 1987/2000 rollbacks innecesarios (99.4%)
  3 chequeos seguidos exigidos: 97/2000 rollbacks innecesarios (4.9%)
```

## Puntos clave

- El conjunto de metricas del gate define, en la practica, que tipos
  de regresion se pueden detectar automaticamente — cualquier
  dimension que no se mida es una dimension en la que un problema real
  puede pasar desapercibido hasta el 100%.
- El numero de chequeos consecutivos exigidos es un tradeoff explicito
  entre sensibilidad (detectar problemas reales rapido) y estabilidad
  (no reaccionar al ruido) — el mismo tipo de balance que el umbral de
  fallas consecutivas de un
  [circuit breaker](../../level2/1-circuit-breaker) o un
  [outlier detector](../../level3/5-outlier-detection).
- El rollback automatico completo (no solo "frenar") es lo que separa
  a estas herramientas de un canary manual: el sistema vuelve solo al
  ultimo estado bueno conocido, sin depender de que una persona lo
  note y actue a tiempo.
- Esto no reemplaza al [kill switch](../2-feature-flags-kill-switch) —
  lo complementa: progressive delivery decide automaticamente si un
  DESPLIEGUE nuevo es seguro; el kill switch es la palanca manual (o
  automatica) para apagar una FUNCIONALIDAD especifica sin tocar el
  despliegue en absoluto.
