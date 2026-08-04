# Leader election con fencing tokens

## Que es

Varios candidatos compiten por un **lock con lease** (tiempo de vida),
otorgado por un servicio de coordinacion (etcd, ZooKeeper, Consul). El
que lo consigue es el lider, y tiene que **renovarlo** antes de que
expire para seguir siendolo. Si no renueva a tiempo, el lock queda
libre y otro candidato puede tomarlo — esa es, literalmente, la
eleccion de un nuevo lider.

Este ejemplo se enfoca en el MECANISMO de eleccion y renovacion en si
mismo. El problema de split-brain por particion de red (el primario
sigue vivo, pero un health check no lo puede alcanzar) ya se ve en
[level3/2-failover](../../level3/2-failover) — aca el escenario es
distinto y igual de real: un lider que nunca se cae, pero se **pausa**
mas tiempo del que dura su lease.

## El escenario de Kleppmann: un lider zombie con lease vencido

Un proceso puede quedar pausado por mucho mas tiempo del esperado sin
haberse caido en absoluto: una pausa larga del garbage collector, un
stall de I/O, una VM migrando de host. Mientras esta pausado, su
lease vence (el servicio de coordinacion no tiene forma de saber si
esta "muerto" o "vivo pero lento" — el mismo problema de fondo que
los [health checks](../../level3/3-health-check)), y otro candidato
toma el liderazgo.

Cuando el proceso original se despierta, **no tiene forma de saber
que paso el tiempo** — su codigo simplemente sigue ejecutandose desde
donde se quedo, creyendose el lider. Si intenta escribir en ese
momento, esa escritura es tan peligrosa como la de cualquier primario
zombie.

## El fencing token: la unica defensa que realmente funciona

Cada vez que el lock cambia de dueño, se entrega un **fencing token**
— un numero que solo crece. El storage compartido rechaza cualquier
escritura con un token mas viejo que el mas alto que ya vio, sin
importar que tan convencido este el que escribe de seguir siendo el
lider. No hace falta que el lider zombie "se entere" de nada — el
storage es quien pone el limite.

## Estructura del ejemplo

- `leader_election.py`: `LeaseLock` (adquisicion y renovacion con
  fencing token creciente) y `FencedStorage` (rechaza escrituras con
  token viejo).
- `demo_leader_election.py`: dos partes.
  1. Eleccion normal, con renovacion a tiempo indefinidamente.
  2. El escenario de Kleppmann: una pausa larga, un nuevo lider
     electo mientras tanto, y el lider zombie rechazado al despertar.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_leader_election.py
```

Salida esperada (TTL del lease = 10s):

```
Parte 2:
  t=0:  A adquiere el lock (fencing token=1)
  t=15: el lease de A ya vencio; B adquiere el lock (fencing token=2)
  t=26: A intenta escribir con su token viejo (1) -> RECHAZADO
  B escribe con su token (2) -> aceptado
```

## Puntos clave

- El lease resuelve "cuanto tiempo puede pasar sin renovar antes de
  que alguien mas pueda tomar el liderazgo" — es un tradeoff: un TTL
  corto detecta caidas reales mas rapido, pero tambien hace mas
  probable que una pausa momentanea (no una caida) dispare una
  eleccion innecesaria.
- El fencing token tiene que verificarse en el RECURSO COMPARTIDO
  (el storage, la cola, el servicio downstream) — verificarlo solo
  del lado del que escribe no sirve de nada, porque el lider zombie
  es precisamente el que no sabe que ya no deberia escribir.
- Esto es la misma idea que el numero de generacion de
  [level3/2-failover](../../level3/2-failover), aplicada a un
  mecanismo de eleccion explicito (lock + lease) en vez de a un
  failover disparado por health checks — dos caminos distintos al
  mismo problema de fondo: nunca confiar en que un nodo sepa por si
  solo si sigue siendo el lider.
- Los relojes de pausa (GC, hypervisor) son mas comunes de lo que
  parece bajo carga alta o en entornos virtualizados — es la razon
  por la que sistemas como Kubernetes usan leases con TTLs de varios
  segundos, no milisegundos, para el liderazgo de sus controladores.
