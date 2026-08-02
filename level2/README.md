# Level 2 — Protección de capacidad compartida

Los ejemplos de [level1](../level1) viven en el camino de **una sola
llamada**: cuanto esperar, cuando reintentar, que devolver si hay que
rendirse. Los de este nivel operan un escalón mas arriba — miran el
trafico **agregado** de muchas llamadas y los **recursos
compartidos** (threads, conexiones, capacidad del backend) por los
que ese trafico compite.

Las preguntas que resuelven estos patrones son de otro tipo:

- ¿Esta dependencia esta degradada de verdad, o fue un tropiezo
  puntual? ¿Vale la pena seguir intentando?
- Si una dependencia se pone lenta, ¿eso deberia poder afectar a
  llamadas hacia OTRAS dependencias que comparten mis recursos?
- ¿Cuanto trafico estoy dispuesto a aceptar, sin importar quien lo
  mande?
- Si no alcanza la capacidad para todos, ¿a quien atiendo primero?
- ¿Como le aviso a quien me manda trabajo que vaya mas despacio?
- Si mil clientes piden lo mismo al mismo tiempo, ¿hace falta
  responderles mil veces?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

No son alternativas entre si — cada uno protege una cosa distinta, y
un sistema real suele necesitar varios a la vez:

```
circuit breaker   -> deja de llamar a una dependencia ya degradada (error o latencia)
bulkhead          -> aisla los recursos del cliente por dependencia, para que
                     una degradada no le robe capacidad a otra sana

rate limiting     -> rechaza trafico que excede una cuota fija de politica
throttling        -> en vez de rechazar, encola y demora el exceso a un ritmo sostenible
load shedding     -> rechaza de inmediato segun PRIORIDAD cuando el sistema
                     esta cerca de su propia capacidad

backpressure      -> el consumidor le hace saber al productor que frene,
                     en vez de que alguien rechace o encole unilateralmente

request coalescing -> deduplica llamadas concurrentes identicas antes de
                      que lleguen al backend
cache defensiva    -> reduce cuanto trafico necesita llegar al backend en
                      primer lugar (stale-while-revalidate, negative
                      caching, expiracion probabilistica)
```

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-circuit-breaker](1-circuit-breaker) | Deja de llamar a una dependencia degradada, ya sea por tasa de error o por tasa de llamadas lentas — maquina de estados CLOSED/OPEN/HALF_OPEN. |
| 2 | [2-bulkhead](2-bulkhead) | Aisla los recursos del cliente por dependencia (semaforo con limite propio), para que una dependencia lenta no le robe capacidad a otras sanas. |
| 3 | [3-rate-limiting](3-rate-limiting) | Compara fixed window, sliding window log y token bucket; el servidor rechaza trafico que supera una cuota fija con `429` + `Retry-After`. |
| 4 | [4-throttling](4-throttling) | En vez de rechazar, encola el exceso con un leaky bucket y lo procesa a un ritmo constante — cambia latencia por disponibilidad. |
| 5 | [5-load-shedding](5-load-shedding) | Rechaza de inmediato segun prioridad (`critical`/`default`/`sheddable`) cuando el sistema esta cerca de su capacidad propia. |
| 6 | [6-backpressure](6-backpressure) | Flujo de control cooperativo: una cola acotada bloquea al productor para que se frene solo, en vez de acumular trabajo sin limite. |
| 7 | [7-request-coalescing](7-request-coalescing) | Single-flight: deduplica llamadas concurrentes por la misma clave, evitando un cache stampede contra el backend. |
| 8 | [8-cache-defensiva](8-cache-defensiva) | Stale-while-revalidate, negative caching y expiracion probabilistica temprana (XFetch) para reducir carga sobre el backend sin sacrificar correctitud. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
