# Resilience Demos

Coleccion de demos pequeños y autocontenidos sobre **patrones de
resiliencia** en sistemas distribuidos. Cada demo aisla un patron,
simula la falla que lo motiva y muestra, con numeros, que pasa con y
sin el patron.

El material esta organizado en **8 niveles** que van ampliando el
radio de la pregunta: desde una sola llamada (timeouts, reintentos)
hasta como se verifica y se opera la resiliencia en produccion
(chaos engineering, SLOs, DR, postmortems).

## Requisitos y uso

- Python 3 (los ejemplos fueron ejecutados con 3.12).
- Solo libreria estandar: **no hay que hacer `pip install`** de nada.

Cada ejemplo vive en su propia carpeta y se ejecuta desde ella (el
nombre del script varia por ejemplo; el README de cada carpeta indica
cual es y la salida esperada):

```bash
cd level1/1-timeout
python3 client_timeout.py
```

## Estructura

```
resilience-demos/
├── level1/ ... level8/
│   ├── README.md                  # indice y motivacion del nivel
│   └── N-nombre-del-patron/
│       ├── README.md              # que es, por que importa, como correrlo
│       └── *.py                   # implementacion y/o demo ejecutable
└── pendientes.md                  # plan original de temas por nivel
```

Convenciones: el README de cada ejemplo explica el patron, la
estructura del codigo, la salida esperada y los puntos clave
(incluyendo sus limites y tradeoffs). Los README hacen referencias
cruzadas entre patrones relacionados, y el codigo evita dependencias
externas para que se pueda leer y modificar facilmente.

## Indice de niveles

| Nivel | Tema | Pregunta central | Ejemplos |
|---|---|---|---|
| [Level 1](level1/README.md) | Fundamentos por peticion | ¿Que hago cada vez que una llamada individual falla o tarda? | 8 |
| [Level 2](level2/README.md) | Proteccion de capacidad compartida | ¿Como evito que el trafico agregado agote recursos compartidos? | 8 |
| [Level 3](level3/README.md) | Redundancia y topologia | ¿Como organizo las replicas para acotar el radio de impacto? | 10 |
| [Level 4](level4/README.md) | Latencia de cola | ¿Como sobrevivo a la variabilidad cuando nada esta "caido"? | 4 |
| [Level 5](level5/README.md) | Consistencia y flujos largos | ¿Que pasa cuando un proceso de varios pasos falla a la mitad? | 8 |
| [Level 6](level6/README.md) | Cambio y despliegue | ¿Como evito causar la falla al desplegar o migrar? | 6 |
| [Level 7](level7/README.md) | Estado distribuido y control | ¿Como se ponen de acuerdo los nodos y como entran y salen del grupo? | 7 |
| [Level 8](level8/README.md) | Verificacion y operacion | ¿Como compruebo que el sistema es resiliente y aprendo de los incidentes? | 5 |

## Contenido detallado

### [Level 1 — Fundamentos por peticion](level1/README.md)

Patrones del camino de una sola llamada.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [timeout](level1/1-timeout) | Acotar cuanto se espera a una dependencia. |
| 2 | [retry](level1/2-retry) | Reintentar fallas transitorias; naive vs backoff + jitter. |
| 3 | [backoff-exp](level1/3-backoff-exp) | Capar el crecimiento del backoff exponencial. |
| 4 | [jitter](level1/4-jitter) | Full, equal y decorrelated jitter vs thundering herd. |
| 5 | [backoff-exp-jitter](level1/5-backoff-exp-jitter) | Backoff exponencial + jitter combinados. |
| 6 | [retry-budget](level1/6-retry-budget) | Limite compartido de reintentos (token bucket). |
| 7 | [idempotency-keys](level1/7-idempotency-keys) | Reintentos seguros de operaciones con efectos secundarios. |
| 8 | [fallback](level1/8-fallback) | Primario → cache → default estatico. |

### [Level 2 — Proteccion de capacidad compartida](level2/README.md)

Trafico agregado y recursos compartidos.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [circuit-breaker](level2/1-circuit-breaker) | Dejar de llamar a una dependencia degradada. |
| 2 | [bulkhead](level2/2-bulkhead) | Aislar recursos por dependencia. |
| 3 | [rate-limiting](level2/3-rate-limiting) | Fixed window, sliding window y token bucket. |
| 4 | [throttling](level2/4-throttling) | Encolar el exceso con leaky bucket. |
| 5 | [load-shedding](level2/5-load-shedding) | Rechazar por prioridad cerca de la capacidad. |
| 6 | [backpressure](level2/6-backpressure) | Frenar al productor con colas acotadas. |
| 7 | [request-coalescing](level2/7-request-coalescing) | Single-flight contra el cache stampede. |
| 8 | [cache-defensiva](level2/8-cache-defensiva) | Stale-while-revalidate, negative caching, XFetch. |

### [Level 3 — Redundancia y topologia](level3/README.md)

Como se organiza la redundancia y como se limita el blast radius.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [redundancia-n1-n2](level3/1-redundancia-n1-n2) | N+1 vs N+2; activo-activo vs activo-pasivo. |
| 2 | [failover](level3/2-failover) | Failover y split-brain; fencing por generacion. |
| 3 | [health-check](level3/3-health-check) | Liveness, readiness y startup. |
| 4 | [load-balancing](level3/4-load-balancing) | RR, least-conn, EWMA, P2C, consistent hashing. |
| 5 | [outlier-detection](level3/5-outlier-detection) | Health checking pasivo con tope de eyeccion. |
| 6 | [multiplexer](level3/6-multiplexer) | Multiplexing y connection pooling. |
| 7 | [replicacion](level3/7-replicacion) | Sync vs async, quorum, leader-follower vs multi-leader. |
| 8 | [sharding](level3/8-sharding) | Sharding simple vs shuffle sharding. |
| 9 | [cell-based-arch](level3/9-cell-based-arch) | Celdas de tamaño fijo con router delgado. |
| 10 | [multi-az](level3/10-multi-az) | Static stability ante la caida de una AZ. |

### [Level 4 — Latencia de cola](level4/README.md)

Sobrevivir a la variabilidad ("The Tail at Scale").

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [hedged-requests](level4/1-hedged-requests) | Copia a otra replica tras superar un umbral. |
| 2 | [tied-requests](level4/2-tied-requests) | Replicas que se cancelan mutuamente. |
| 3 | [deadline-propagation](level4/3-deadline-propagation) | Presupuesto de latencia a lo largo de la cadena. |
| 4 | [cancelacion-propagada](level4/4-cancelacion-propagada) | Liberar trabajo cuyo cliente ya se rindio. |

### [Level 5 — Consistencia y flujos largos](level5/README.md)

Procesos de negocio de varios pasos y servicios.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [saga](level5/1-saga) | Compensaciones; orquestada vs coreografiada. |
| 2 | [transactional-outbox-inbox](level5/2-transactional-outbox-inbox) | Estado y evento en la misma transaccion. |
| 3 | [consumidor-idempotente-dedup](level5/3-consumidor-idempotente-dedup) | Deduplicacion para at-least-once. |
| 4 | [dead-letter-queue](level5/4-dead-letter-queue) | Aislar poison pills y reprocesar. |
| 5 | [checkpointing-durable-execution](level5/5-checkpointing-durable-execution) | Workflows que sobreviven a la muerte del worker. |
| 6 | [reconciliation-loops](level5/6-reconciliation-loops) | Deseado vs real, al estilo Kubernetes. |
| 7 | [anti-entropy-read-repair-merkle](level5/7-anti-entropy-read-repair-merkle) | Reparar replicas divergentes con arboles de Merkle. |
| 8 | [event-sourcing](level5/8-event-sourcing) | Reconstruir estado desde el log de eventos. |

### [Level 6 — Cambio y despliegue](level6/README.md)

La mayoria de las caidas las causa un cambio, no el hardware.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [canary-blue-green-rolling](level6/1-canary-blue-green-rolling) | Radio de impacto segun la estrategia de deploy. |
| 2 | [feature-flags-kill-switch](level6/2-feature-flags-kill-switch) | Desactivar sin desplegar; rollout gradual. |
| 3 | [progressive-delivery-auto-rollback](level6/3-progressive-delivery-auto-rollback) | Auto-rollback por SLO. |
| 4 | [expand-contract-migrations](level6/4-expand-contract-migrations) | Migraciones de esquema compatibles. |
| 5 | [tolerant-reader](level6/5-tolerant-reader) | Ley de Postel y campos desconocidos. |
| 6 | [immutable-infrastructure](level6/6-immutable-infrastructure) | Reemplazar en lugar de mutar. |

### [Level 7 — Estado distribuido y control](level7/README.md)

Los mecanismos de bajo nivel detras de "hay un lider" o "hay capacidad".

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [leader-election-fencing-tokens](level7/1-leader-election-fencing-tokens) | Lider con lease y fencing tokens. |
| 2 | [leases-heartbeats-phi-accrual](level7/2-leases-heartbeats-phi-accrual) | Deteccion adaptativa de fallas. |
| 3 | [consensus-raft-paxos](level7/3-consensus-raft-paxos) | Quorum de mayoria y acuerdo. |
| 4 | [gossip](level7/4-gossip) | Difusion de membresia sin coordinador. |
| 5 | [graceful-shutdown](level7/5-graceful-shutdown) | SIGTERM, preStop y connection draining. |
| 6 | [autoscaling](level7/6-autoscaling) | Reactivo vs predictivo y sus limites. |
| 7 | [constant-work-pattern](level7/7-constant-work-pattern) | Eliminar la bimodalidad. |

### [Level 8 — Verificacion y operacion](level8/README.md)

Como se comprueba la resiliencia y como se aprende de los incidentes.

| # | Ejemplo | Tema |
|---|---|---|
| 1 | [chaos-engineering](level8/1-chaos-engineering) | Hipotesis y experimentos con radio de impacto acotado. |
| 2 | [slo-error-budgets](level8/2-slo-error-budgets) | Presupuesto de error y burn rate. |
| 3 | [observabilidad-red-use-traces](level8/3-observabilidad-red-use-traces) | RED, USE, trazas y percentiles vs promedios. |
| 4 | [dr-rto-rpo](level8/4-dr-rto-rpo) | Estrategias de DR; probar el restore. |
| 5 | [runbooks-postmortems](level8/5-runbooks-postmortems) | Runbooks y postmortems sin culpa. |

## Orden de lectura sugerido

Los niveles son acumulativos: `level1 → level2 → ... → level8`. Cada
uno asume los conceptos del anterior y varios README enlazan a
patrones de otros niveles (por ejemplo, el constant work pattern del
level 7 con los reconciliation loops del level 5 y el DR del level 8).

Si buscas un problema concreto:

| Si te preocupa... | Empieza por |
|---|---|
| Llamadas lentas o fallidas | Level 1 |
| Una dependencia que arrastra al resto | Level 2 |
| La caida de una instancia, AZ o region | Level 3 |
| El p99 alto con todo "sano" | Level 4 |
| Procesos a medias, mensajes duplicados o perdidos | Level 5 |
| Caidas causadas por deploys y migraciones | Level 6 |
| Lideres, consenso, apagados y escalado | Level 7 |
| Probar y operar todo lo anterior | Level 8 |
