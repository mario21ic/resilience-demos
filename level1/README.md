# Level 1 — Fundamentos por petición

Los ejemplos de este nivel son los patrones de resiliencia que viven
en el **camino de una sola llamada**: el codigo que envuelve un
request individual (o una operacion logica compuesta por ese request
y sus reintentos) desde que el cliente lo dispara hasta que obtiene
una respuesta — real o de emergencia.

No tratan sobre como proteger un sistema completo de una dependencia
ampliamente degradada (eso son patrones estructurales — circuit
breakers, bulkheads, rate limiting — de niveles siguientes), sino
sobre las decisiones que hay que tomar **cada vez que un cliente le
pide algo a otro servicio**:

- ¿Cuanto estoy dispuesto a esperar?
- Si falla, ¿tiene sentido reintentar?
- Si reintento, ¿cuanto espero antes del siguiente intento?
- Si muchos clientes reintentan a la vez, ¿como evito que colisionen?
- ¿Hay un limite global a cuantos reintentos me puedo permitir?
- Si la operacion tiene efectos secundarios, ¿como reintento sin
  duplicarlos?
- Si me rindo, ¿que le devuelvo a quien me llamo a mi?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

Estos patrones no son alternativas entre si — son capas que se van
apilando sobre la misma llamada:

```
timeout            -> acota cuanto dura CADA intento
  └─ retry          -> decide si vale la pena intentar de nuevo
       └─ backoff   -> decide cuanto esperar antes del siguiente intento
            └─ jitter -> evita que esa espera coincida con la de otros clientes
retry budget        -> limite global a los reintentos de TODOS los clientes juntos
idempotency keys    -> hace seguro reintentar operaciones con efectos secundarios
fallback            -> que devolver cuando ya no hay mas reintentos posibles
```

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-timeout](1-timeout) | Acotar cuanto espera un cliente a una dependencia antes de abortar y fallar rapido. |
| 2 | [2-retry](2-retry) | Reintentar fallas transitorias: naive (sin espera) vs. con backoff exponencial + jitter, y que pasa cuando la falla es permanente. |
| 3 | [3-backoff-exp](3-backoff-exp) | Como topar el crecimiento del backoff exponencial: delay capado (`capped`) vs. exponente truncado (`truncated`), y por que un cap por intento no reemplaza un presupuesto de tiempo total. |
| 4 | [4-jitter](4-jitter) | Las tres variantes de jitter de AWS (full, equal, decorrelated): forma de cada distribucion y su efecto real mitigando el thundering herd. |
| 5 | [5-backoff-exp-jitter](5-backoff-exp-jitter) | Vista combinada de backoff exponencial + jitter en un solo ejemplo (complementa a 3 y 4, que los tratan por separado). |
| 6 | [6-retry-budget](6-retry-budget) | Limite compartido (token bucket, al estilo gRPC) a cuantos reintentos se permiten en total, para no sumar carga extra sobre un backend ya degradado. |
| 7 | [7-idempotency-keys](7-idempotency-keys) | Como reintentar de forma segura operaciones con efectos secundarios (cobros, creacion de pedidos) sin duplicarlos. |
| 8 | [8-fallback](8-fallback) | Cadena de fallback (primario -> cache -> default estatico) para cuando ya se agotaron los reintentos. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4` (o `5` como resumen de `3+4`) `-> 6 -> 7 -> 8`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
