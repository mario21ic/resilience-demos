# Level 5 — Consistencia y flujos largos

Los niveles anteriores tratan sobre una llamada, una dependencia, una
topologia de replicas. Este trata sobre algo que dura mas: procesos de
negocio que abarcan varios servicios, varios pasos, y a veces varios
dias — donde no hay una transaccion unica que lo cubra todo, y donde
"fallo a mitad de camino" es un estado que hay que saber manejar, no
solo evitar.

Las preguntas de este nivel:

- Si un proceso de negocio que ya avanzo parcialmente falla a mitad de
  camino, ¿como se deshace lo que ya se hizo?
- ¿Como se garantiza que un cambio de estado y el evento que lo
  anuncia no puedan ocurrir el uno sin el otro?
- Si un mensaje puede llegar mas de una vez, ¿como se logra que
  aplicarlo dos veces sea igual que aplicarlo una?
- ¿Que se hace con el mensaje que falla siempre, sin bloquear a todos
  los que vienen detras?
- ¿Como sobrevive un workflow largo a que el proceso que lo ejecuta se
  caiga a mitad de camino?
- En vez de corregir un problema puntual, ¿como se construye un
  sistema que converge solo hacia el estado correcto, sin importar
  que lo desvio?
- ¿Como se reparan replicas que divergieron, sin comparar todo contra
  todo?
- ¿Que pasa si el estado derivado se corrompe — hace falta un backup
  aparte, o alcanza con lo que ya se tiene?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

```
saga                          -> deshacer un proceso de negocio parcial
                                  con compensaciones, orquestadas o coreografiadas

transactional outbox/inbox    -> escritura + evento, atomicos
consumidor idempotente/dedup  -> aplicar el mismo mensaje 2 veces = aplicarlo 1 vez
dead letter queue             -> aislar el mensaje que falla siempre, sin bloquear la cola

checkpointing/durable exec    -> un workflow sobrevive a la muerte de su worker
reconciliation loops          -> converger hacia el estado deseado, continuamente
anti-entropy/read repair/merkle -> reparar replicas divergentes, a escala
event sourcing                -> el estado se reconstruye desde un log, nunca es la fuente de verdad
```

Los primeros cuatro (saga, outbox/inbox, dedup, DLQ) son las
herramientas basicas de mensajeria confiable. Los ultimos cuatro
(checkpointing, reconciliation, anti-entropy, event sourcing)
comparten una misma idea de fondo: en vez de intentar que cada
operacion sea perfecta, se acepta que van a pasar cosas (workers que
mueren, replicas que divergen, estado que se corrompe) y se invierte
en la capacidad de **reconstruir o converger** despues del hecho.

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-saga](1-saga) | Transacciones distribuidas con compensaciones; orquestada (un coordinador central) vs coreografiada (eventos entre servicios independientes). |
| 2 | [2-transactional-outbox-inbox](2-transactional-outbox-inbox) | Escribir el cambio de estado y el evento que lo anuncia en la misma transaccion, con SQLite real. |
| 3 | [3-consumidor-idempotente-dedup](3-consumidor-idempotente-dedup) | Idempotencia natural, deduplicacion con ventana (TTL) y sus limites frente a redeliveries muy tardias. |
| 4 | [4-dead-letter-queue](4-dead-letter-queue) | Aislar el mensaje que falla siempre (poison pill) para que no bloquee la cola; reproceso con y sin arreglar la causa raiz. |
| 5 | [5-checkpointing-durable-execution](5-checkpointing-durable-execution) | Un workflow largo sobrevive a la muerte de su worker reproduciendo un historial durable — el modelo de Temporal/Step Functions. |
| 6 | [6-reconciliation-loops](6-reconciliation-loops) | El modelo de control de Kubernetes: comparar deseado vs real continuamente, por nivel en vez de por evento. |
| 7 | [7-anti-entropy-read-repair-merkle](7-anti-entropy-read-repair-merkle) | Reparar replicas divergentes al leer (read repair) y en el fondo (anti-entropy), usando arboles de Merkle para no comparar todo. |
| 8 | [8-event-sourcing](8-event-sourcing) | El estado se deriva de un log de eventos, nunca es la fuente de verdad — reconstruccion tras corrupcion, multiples proyecciones, snapshots. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
