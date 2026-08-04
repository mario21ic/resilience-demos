# Leases y heartbeats; phi accrual failure detector

## Que es

La forma mas comun de detectar que un nodo sigue vivo es que mande
una señal periodica ("heartbeat"), y considerarlo caido si esa señal
no llega dentro de un tiempo esperado — el mismo concepto de lease
que en [leader election](../1-leader-election-fencing-tokens), pero
aplicado a membresia/salud en general, no solo a un lock de
liderazgo.

## El problema de un timeout fijo

La red real tiene **jitter**: variacion normal en cuanto tardan los
mensajes en llegar. Un detector de timeout fijo tiene que elegir entre
dos malos extremos: ser generoso (tarda en detectar caidas reales) o
agresivo (declara "muerto" a un nodo sano cada vez que el jitter
normal supera el umbral).

## Phi accrual: un detector que se adapta solo

El **phi accrual failure detector** (usado en Cassandra y Akka)
reemplaza la decision binaria por un valor continuo, `phi`, que mide
que tan **sorprendente** es no haber recibido un heartbeat en este
tiempo, dado el **historial** de intervalos observados para ESE nodo
en particular:

- Si los heartbeats de un nodo siempre fueron muy regulares, una
  demora chica ya genera un `phi` alto — el detector es sensible,
  porque esa regularidad hace que un retraso sea mas sospechoso.
- Si siempre fueron variables, el mismo retraso genera un `phi` mas
  bajo — el detector tolera esa variabilidad porque ya es "normal"
  para ese nodo.

No hace falta configurar un timeout distinto por nodo a mano: el
detector aprende el comportamiento normal de cada uno a partir de sus
propios heartbeats.

## Estructura del ejemplo

- `phi_accrual.py`: `PhiAccrualDetector`, que mantiene una ventana de
  intervalos observados y calcula `phi` asumiendo que siguen una
  distribucion normal.
- `demo_phi_accrual.py`: dos partes.
  1. Un detector de timeout fijo sobre 100 heartbeats sanos con
     jitter normal — cuantas falsas alarmas genera.
  2. El mismo historial medido con phi accrual, mas que pasa cuando
     los heartbeats realmente dejan de llegar.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_phi_accrual.py
```

Salida esperada:

```
Parte 1: timeout fijo de 2s -> 8/100 heartbeats sanos declarados 'muerto' por error

Parte 2: mismo historial, phi maximo durante la fase sana = 5.63 (umbral: 8)
         -> cero falsas alarmas

  tras dejar de recibir heartbeats:
    3s sin heartbeat: phi=4.95
    5s sin heartbeat: phi=16.00 <- SOSPECHOSO
```

## Puntos clave

- Phi accrual no elimina el tradeoff sensibilidad/estabilidad — lo
  hace **adaptativo por nodo**, en vez de exigir un unico numero fijo
  que sirva igual de bien para todos.
- El umbral de `phi` (tipicamente 8, como en Akka) sigue siendo una
  decision de politica — mas alto tolera mas jitter a costa de
  detectar fallas reales mas lento; mas bajo hace lo opuesto.
- Este detector responde "que tan sospechoso es este nodo ahora
  mismo", no "esta vivo o muerto" — la decision de que hacer con eso
  (sacarlo de un pool, iniciar una eleccion) sigue siendo una logica
  aparte, igual que en
  [outlier detection](../../level3/5-outlier-detection).
- Se combina naturalmente con leases: el TTL de un lease puede fijarse
  de forma mucho mas ajustada si la deteccion de "el dueño sigue vivo"
  es adaptativa, en vez de asumir el peor jitter posible para todos
  los nodos por igual.
