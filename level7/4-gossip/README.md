# Gossip

## Que es

Gossip es como se difunde membresia (o cualquier informacion) en un
cluster grande **sin un coordinador central** y sin que cada nodo
necesite hablar con todos los demas. En cada ronda, cada nodo que ya
conoce una novedad se la cuenta a un puñado de nodos elegidos **al
azar** — no a todos, no siguiendo una jerarquia fija. La informacion
se propaga "epidemicamente", como un rumor, hasta cubrir todo el
cluster.

Es el mecanismo detras de Cassandra (membresia y deteccion de fallas)
y de Consul/Serf (el protocolo SWIM), entre otros sistemas que
necesitan que miles de nodos converjan en la misma vista del cluster
sin depender de un punto unico de coordinacion.

## Por que es tan rapido: crecimiento epidemico

Si cada nodo informado le cuenta la novedad a 1 nodo nuevo por ronda,
la cantidad de nodos informados se **duplica** aproximadamente en
cada ronda (mientras queden muchos nodos sin informar) — el mismo
crecimiento que una epidemia o un rumor viral. Eso significa que un
cluster de 1000 nodos se entera completo en un puñado de rondas
(**logaritmico** respecto al tamaño), no en 1000 rondas.

## Por que es tan resistente: no hay un camino unico

Como cada nodo elige a quien contarle al azar, existen muchisimos
caminos posibles por los que una novedad puede llegar de un nodo a
otro. Perder una fraccion del cluster (nodos caidos, una particion de
red) no rompe la propagacion — simplemente hay menos nodos
participando, pero los que quedan vivos igual convergen, casi al
mismo ritmo.

## Estructura del ejemplo

- `gossip.py`: `simulate_gossip` (la propagacion epidemica, con o sin
  nodos caidos) y `simulate_centralized_broadcast` (el contraste con
  un unico coordinador).
- `demo_gossip.py`: tres partes.
  1. Propagacion en un cluster de 1000 nodos sin fallas.
  2. Lo mismo con el 30% de los nodos caidos.
  3. Que pasa si, en cambio, hubiera un unico coordinador central y
     ese coordinador fuera uno de los caidos.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_gossip.py
```

Salida esperada:

```
Parte 1 (1000 nodos, sin fallas): converge en 16 rondas
         progreso: [1, 2, 4, 8, 16, 32, 59, 113, ...]

Parte 2 (30% de nodos caidos): converge en 17 rondas sobre los 700 vivos
         (casi identico a la Parte 1)

Parte 3 (coordinador central caido): 0/700 nodos informados
```

## Puntos clave

- El "fanout" (a cuantos nodos le cuenta cada uno por ronda) es un
  tradeoff directo entre velocidad de convergencia y trafico de red
  generado — mas fanout converge mas rapido, pero cada nodo manda mas
  mensajes por ronda.
- Gossip da **consistencia eventual**, no inmediata: durante las
  primeras rondas, distintos nodos del cluster todavia tienen vistas
  distintas de la realidad — el mismo tipo de ventana que
  [replicacion asincrona](../../level3/7-replicacion).
- La ausencia de un coordinador central es la clave de la robustez:
  no hay ningun nodo cuya caida detenga la propagacion para el resto
  — cada nodo es, a la vez, tan importante y tan reemplazable como
  cualquier otro.
- Esto se combina naturalmente con
  [phi accrual](../2-leases-heartbeats-phi-accrual): gossip es como
  la informacion de "quien esta vivo" circula por el cluster; phi
  accrual es como cada nodo decide, con esa informacion, si sospechar
  que otro esta caido.
