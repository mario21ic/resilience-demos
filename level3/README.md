# Level 3 — Redundancia y topología

Los ejemplos de [level1](../level1) viven en una sola llamada; los de
[level2](../level2) protegen la capacidad compartida dentro de un
mismo proceso o servicio. Los de este nivel dan un paso mas arriba
todavia: como esta **organizada fisicamente** la redundancia entre
varias instancias, zonas, regiones y replicas de datos — y, sobre
todo, como esa organizacion **limita el radio de impacto** cuando algo
falla.

Las preguntas que resuelven estos patrones son de topologia y diseño
de sistema, no de una llamada individual:

- ¿Cuantas copias de cada cosa hacen falta para tolerar N fallas
  simultaneas, y como se organizan (todas sirviendo trafico, o unas
  de guardia)?
- ¿Como se detecta y se reacciona a que una replica esta enferma —
  activamente (preguntandole) o pasivamente (mirando trafico real)?
- ¿Como se reparte el trafico entre replicas sanas, y como se evita
  que una sola le robe capacidad a las demas?
- ¿Cuantas copias de un dato existen, y que se gana o se pierde
  segun cuando se confirma una escritura y cuantas replicas hacen
  falta para leerla de forma segura?
- ¿Como se evita que un cliente toxico, un shard caliente o una AZ
  caida afecten a mas que una fraccion chica y conocida del resto del
  sistema?
- ¿Que pasa cuando la recuperacion misma depende de un sistema que
  puede estar degradado justo cuando mas se lo necesita?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

```
redundancia N+1/N+2   -> cuanta capacidad de sobra hay, y como esta organizada
     └─ failover        -> como se pasa el trafico a esa capacidad de sobra,
                            y como evitar split-brain al hacerlo
          └─ health checks    -> como se detecta activamente que algo esta mal
          └─ outlier detection -> como se detecta pasivamente, mirando trafico real
               └─ load balancing -> como se reparte trafico entre lo que sigue sano

replicacion   -> cuantas copias de un DATO existen y cuando se confirma un write
sharding      -> como se reparte el trabajo/datos para acotar el radio de impacto
     └─ cell-based architecture -> la misma idea aplicada al SERVICIO entero
     └─ multi-AZ / static stability -> la misma idea a nivel de infraestructura,
                                        con el matiz de no depender del control plane

multiplexer (sintesis del lado del cliente) -> pool + LB + circuit breaker + failover
                                                empaquetados detras de una sola llamada
```

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-redundancia-n1-n2](1-redundancia-n1-n2) | N+1 vs N+2 (cuantas fallas simultaneas se toleran) y activo-activo vs activo-pasivo (como esta organizada esa capacidad de sobra). |
| 2 | [2-failover](2-failover) | Failover automatico vs manual disparado por health checks, y por que el enemigo real es el split-brain — la defensa estructural es fencing por generacion. |
| 3 | [3-health-check](3-health-check) | Liveness, readiness y startup; por que un chequeo profundo en el probe o la dependencia equivocada propaga fallas en cascada. |
| 4 | [4-load-balancing](4-load-balancing) | Round robin, least-connections, EWMA, P2C (power of two choices) y consistent hashing con bounded loads. |
| 5 | [5-outlier-detection](5-outlier-detection) | Health checking pasivo: sacar del pool a la replica enferma en base a trafico real, con backoff de ejeccion y un tope para no eyectar a todo el pool. |
| 6 | [6-multiplexer](6-multiplexer) | Multiplexing y connection pooling (HTTP/2, gRPC): reducen el costo de conexion y habilitan hedging barato; el "multiplexer" es en realidad pool + LB + circuit breaker + failover. |
| 7 | [7-replicacion](7-replicacion) | Replicacion sincrona vs asincrona, quorum (W+R>N), y leader-follower vs multi-leader con el riesgo de LWW ante relojes desincronizados. |
| 8 | [8-sharding](8-sharding) | Sharding simple vs shuffle sharding: como una combinacion de shards por tenant reduce drasticamente el blast radius de un vecino toxico. |
| 9 | [9-cell-based-arch](9-cell-based-arch) | Celdas de tamaño fijo y probado con un router delgado — el radio de impacto queda constante sin importar cuanto crezca el sistema. |
| 10 | [10-multi-az](10-multi-az) | Static stability: la recuperacion ante la caida de una AZ no debe depender de un control plane que suele estar degradado justo durante el incidente. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 5 -> 4 -> 7 -> 8 -> 9 -> 10 -> 6`.

Los ejemplos 6 y 9 son sintesis que combinan varios de los anteriores
(pool, load balancing, circuit breaker, failover, redundancia,
sharding) — se aprovechan mejor despues de haber visto las piezas por
separado.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
