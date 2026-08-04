# Level 7 — Estado distribuido y control

Los niveles anteriores dan por sentado que "hay un lider", "las
replicas se reparan solas", "la capacidad esta ahi cuando hace
falta". Este nivel mira los mecanismos de mas bajo nivel que hacen
posible cada una de esas suposiciones: como se elige un lider sin
ambiguedad, como se detecta que un nodo sigue vivo, como muchos nodos
se ponen de acuerdo sobre un unico estado, como se apaga un proceso
sin romper nada, y por que agregar capacidad tiene limites que ningun
autoscaler puede superar.

Las preguntas de este nivel:

- ¿Como se elige un lider entre varios candidatos, y que pasa si el
  lider "electo" en realidad nunca se cayo, solo estuvo pausado mas
  tiempo del esperado?
- ¿Como se decide que un nodo esta muerto sin generar falsas alarmas
  por el jitter normal de la red?
- ¿Como logran muchos nodos ponerse de acuerdo sobre una unica
  secuencia de cambios, tolerando fallas?
- ¿Como se entera un cluster grande de un cambio de membresia sin un
  coordinador central?
- ¿Como se apaga un proceso sin cortar el trabajo que ya tenia en
  curso?
- ¿Que tan rapido puede reaccionar el autoscaling, y que pasa cuando
  el problema crece mas rapido que eso?
- ¿Como se diseña un sistema para que su "modo crisis" sea el mismo
  camino de codigo que su modo normal?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

```
leader election + fencing tokens  -> como se elige un lider sin ambiguedad,
                                      y como se evita que uno "zombie" haga daño
leases y heartbeats + phi accrual -> como se detecta que un nodo sigue vivo
consenso (Raft/Paxos)             -> como el propio grupo de nodos logra
                                      acuerdo, sin depender de un lock externo
gossip                            -> como se difunde membresia sin
                                      coordinador central, tolerando particiones

graceful shutdown  -> como un nodo se va del grupo sin romper nada
autoscaling        -> cuanta capacidad nueva se puede sumar, y que tan rapido
constant work      -> por que el "modo crisis" deberia ser el modo de siempre
```

Los primeros cuatro son variaciones sobre el mismo problema central:
como varios nodos se ponen de acuerdo sobre un estado compartido
(quien es el lider, quien sigue vivo, que paso, quien esta en el
grupo) sin un arbitro externo infalible. Los ultimos tres son sobre
el ciclo de vida de la capacidad: como entra y sale un nodo del
sistema, y los limites reales de escalar bajo presion.

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-leader-election-fencing-tokens](1-leader-election-fencing-tokens) | Eleccion de lider con lock + lease; el escenario de Kleppmann de un lider pausado (no caido) que despierta creyendose vigente. |
| 2 | [2-leases-heartbeats-phi-accrual](2-leases-heartbeats-phi-accrual) | Deteccion adaptativa de fallas: un valor continuo de sospecha que se ajusta al jitter normal de cada nodo, en vez de un timeout fijo. |
| 3 | [3-consensus-raft-paxos](3-consensus-raft-paxos) | Por que el quorum de mayoria simple garantiza que dos lideres nunca ganen a la vez, y que una entrada comprometida nunca se pierda. |
| 4 | [4-gossip](4-gossip) | Difusion epidemica de membresia: cobertura de todo un cluster en rondas logaritmicas, tolerante a perder una fraccion de los nodos. |
| 5 | [5-graceful-shutdown](5-graceful-shutdown) | SIGTERM con periodo de gracia vs SIGKILL; la carrera de desregistro que el hook `preStop` existe para cubrir. |
| 6 | [6-autoscaling](6-autoscaling) | Reactivo vs predictivo, y por que el autoscaling nunca puede reaccionar mas rapido que su propio tiempo de deteccion + aprovisionamiento. |
| 7 | [7-constant-work-pattern](7-constant-work-pattern) | Eliminar la bimodalidad: hacer siempre la misma cantidad de trabajo para que el "modo crisis" sea el modo de siempre, probado en cada ciclo. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
