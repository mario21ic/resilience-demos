# Consenso (Raft, Paxos)

## Que es

Consenso es como varios nodos se ponen de acuerdo sobre **un unico**
lider y **una unica** secuencia de cambios de estado, incluso con
nodos que fallan o mensajes que se pierden. Raft y Paxos son los dos
protocolos de consenso mas usados (etcd, Consul y la mayoria de las
bases de datos distribuidas modernas usan Raft; Paxos es el original,
mas viejo y mas dificil de implementar correctamente).

La pieza central de ambos es el **quorum de mayoria simple**
(`N//2 + 1` de N nodos), usado para dos cosas:

1. **Elegir lider**: un candidato necesita el voto de una mayoria
   para ganar.
2. **Confirmar una entrada del log**: un cambio solo se considera
   comprometido (seguro, durable) cuando una mayoria de nodos ya lo
   tiene.

## Por que mayoria simple, y no cualquier otro numero

Es una propiedad matematica, no una convencion arbitraria: dos
subconjuntos mayoritarios de un mismo conjunto **siempre** se
solapan en al menos un nodo. Si no se solaparan, sus tamaños
sumarian mas que el total de nodos — una contradiccion. Esa garantia
de solapamiento es la que hace posible:

- Que **dos candidatos nunca puedan ganar una eleccion al mismo
  tiempo** (sumarian mas votos que nodos existen).
- Que **una entrada comprometida nunca se pierda**, sin importar que
  nodos fallen despues: cualquier mayoria futura (por ejemplo, los
  votantes de la proxima eleccion) esta garantizada de incluir al
  menos un nodo que ya tiene esa entrada.

## Estructura del ejemplo

- `consensus.py`: `run_election` (cuenta votos y determina el
  ganador), `is_safe_from_future_majorities` (verifica la garantia de
  solapamiento para una entrada dada).
- `demo_consensus.py`: dos partes.
  1. Eleccion de lider: un split limpio (gana uno), un split
     fragmentado (nadie gana, hace falta otra ronda), y por que dos
     candidatos nunca pueden ganar a la vez.
  2. Una entrada replicada a una mayoria esta a salvo de cualquier
     eleccion futura; una que no llego a mayoria puede perderse.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_consensus.py
```

Salida esperada (5 nodos, mayoria=3):

```
Parte 1: votos A=3,B=2 -> gana A
         votos A=2,B=2,C=1 -> gana nadie (voto fragmentado)

Parte 2: entrada en {0,1,2} (mayoria) -> a salvo de cualquier eleccion futura: True
         entrada en {0,1} (no es mayoria) -> a salvo: False
```

## Puntos clave

- Un voto fragmentado (ningun candidato llega a mayoria) no es un
  fallo del protocolo — es un resultado valido que simplemente
  requiere otra ronda. Raft usa timeouts de eleccion aleatorios
  especificamente para reducir la probabilidad de que se repita el
  mismo fragmentado ronda tras ronda.
- "Comprometido" (committed) es una propiedad binaria y permanente:
  una vez que una entrada llego a mayoria, nunca deja de estar a
  salvo — no hace falta re-verificarlo despues de cada falla nueva.
- Esta es la misma matematica de solapamiento que
  [quorum en replicacion](../../level3/7-replicacion) (W+R>N), pero
  aplicada especificamente a que TODOS los nodos compartan una unica
  secuencia de decisiones, no solo a que una lectura vea el ultimo
  valor escrito.
- Raft y Paxos resuelven el mismo problema que
  [leader election con fencing tokens](../1-leader-election-fencing-tokens)
  resuelve con un lock externo (etcd, ZooKeeper) — la diferencia es
  que el consenso construye esa garantia DESDE ADENTRO del propio
  grupo de nodos, sin depender de un servicio de coordinacion externo.
