# 1. Circuit breaker (tasa de error y latencia)

## Que es

Timeout y retry ([level1](../../level1)) operan sobre **una sola
llamada**. El circuit breaker mira el **patron** de las ultimas
llamadas: si una fraccion suficiente de ellas esta fallando, o
tardando demasiado, asume que la dependencia esta degradada y deja de
intentar por un rato — protegiendola (y protegiendo al propio cliente)
de seguir golpeando algo que ya sabemos que no va a responder bien.

Es el mismo nombre que el disyuntor electrico: cuando detecta una
condicion peligrosa, "corta el circuito" para evitar dano mayor, y
solo lo vuelve a cerrar despues de comprobar que ya es seguro hacerlo.

## Dos causas de disparo, no solo una

Muchas implementaciones de circuit breaker (este ejemplo sigue el
modelo de [resilience4j](https://resilience4j.readme.io/docs/circuitbreaker))
evaluan dos condiciones independientes sobre una ventana deslizante de
llamadas recientes:

- **Tasa de error**: que fraccion de las ultimas N llamadas termino en
  excepcion/error.
- **Tasa de llamadas lentas**: que fraccion de las ultimas N llamadas
  supero un umbral de duracion, **aunque hayan sido exitosas**.

Esto ultimo es clave y se suele pasar por alto: una dependencia puede
no estar devolviendo ningun error y sin embargo estar degradada -
respondiendo cada vez mas lento hasta agotar threads, conexiones o
colas del lado del cliente. Si el circuit breaker solo mirara errores,
nunca dispararia en ese escenario.

## Maquina de estados

```
   CLOSED ──(tasa de error o de lentitud supera el umbral)──> OPEN
      ^                                                         │
      │                                            (pasa reset_timeout)
      │                                                         v
      └──(llamadas de prueba OK y rapidas)── HALF_OPEN <────────┘
                                                  │
                                    (una llamada de prueba falla o es lenta)
                                                  v
                                                 OPEN
```

- **CLOSED**: las llamadas pasan normalmente; cada resultado
  (exito/falla, duracion) se registra en una ventana de tamano fijo.
- **OPEN**: toda llamada se rechaza de inmediato (`CircuitOpenError`),
  sin siquiera intentar la llamada real, hasta que pasa
  `reset_timeout`.
- **HALF_OPEN**: se dejan pasar unas pocas llamadas de prueba. Si
  todas son exitosas y rapidas, el circuito cierra. Si alguna falla o
  es lenta, vuelve a abrirse inmediatamente.

## Estructura del ejemplo

- `circuit_breaker.py`: la clase `CircuitBreaker`, independiente de
  cualquier llamada de red — envuelve cualquier funcion (`breaker.call(func)`).
- `server.py`: dependencia simulada con comportamiento configurable
  (`GET /admin/behavior?state=healthy|error|slow`).
- `client_circuit_breaker.py`: dos recorridos completos contra la
  misma dependencia:
  - **Parte A**: el backend empieza a devolver `500` -> el circuito
    abre por **tasa de error**.
  - **Parte B**: el backend sigue devolviendo `200 OK`, pero tarda
    0.5s (por encima del umbral de 0.3s) -> el circuito abre por
    **tasa de llamadas lentas**, sin que haya ocurrido ni un solo
    error HTTP.

  En ambas partes se recorre el ciclo completo:
  `CLOSED -> OPEN -> HALF_OPEN (reabre si sigue mal) -> HALF_OPEN -> CLOSED`.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_circuit_breaker.py
```

Salida esperada (resumen):

```
Parte A: el circuito abre por TASA DE ERROR
  call 3     -> FALLA real (500)  [circuito: open]
  call 4     -> RECHAZADA sin llamar al backend (circuito abierto)
  motivo de apertura: tasa de error 50% >= 50%

Parte B: el circuito abre por TASA DE LLAMADAS LENTAS
  call 3     -> OK: 'ok (lento)'  [circuito: open]
  call 4     -> RECHAZADA sin llamar al backend (circuito abierto)
  motivo de apertura: tasa de llamadas lentas 50% >= 50%
```

En la Parte B, todas las llamadas devolvieron `200 OK` — el circuito
igual abrio, porque la lentitud sostenida es en si misma una senal de
degradacion.

## Puntos clave

- Un circuit breaker actua sobre el **patron** de varias llamadas, no
  sobre una sola — es la pieza que falta entre "esta llamada fallo"
  (timeout/retry) y "esta dependencia esta degradada".
- Medir solo errores no alcanza: una dependencia lenta pero "exitosa"
  puede ser tan daniña como una caida, porque sigue consumiendo
  threads/conexiones/timeouts del cliente. Por eso conviene un umbral
  de latencia ademas de uno de error.
- El estado `HALF_OPEN` evita dos extremos: reabrir el trafico de
  golpe (podria re-tumbar algo que recien se esta recuperando) o
  quedarse abierto para siempre (nunca se entera si ya se recupero).
- El circuit breaker y el retry ([2-retry](../../level1/2-retry)) se
  combinan naturalmente: cuando el circuito esta abierto, ni siquiera
  vale la pena reintentar — fallar rapido y usar un
  [fallback](../../level1/8-fallback) es la respuesta correcta.
