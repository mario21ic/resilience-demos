# Level 4 — Latencia de cola (tail latency)

Los niveles anteriores tratan sobre sobrevivir a una falla. Este trata
sobre algo mas sutil: sobrevivir a la **variabilidad**, incluso cuando
nada esta técnicamente "caido". Un sistema puede tener un p50
excelente y un p99 pesimo — cada replica individual casi siempre
responde rapido, pero con suficiente escala (miles de requests por
segundo, o un solo request que agrega resultados de cientos de
replicas), la probabilidad de que **algo** en el camino sea lento se
vuelve alta.

Las preguntas de este nivel son sobre esa cola larga:

- Si una llamada va lenta, ¿vale la pena disparar una copia a otra
  replica? ¿Antes o despues de saber que va lenta?
- ¿Cuanto tiempo le queda realmente al cliente que origino todo esto,
  y como se entera cada capa intermedia de la cadena?
- Cuando el cliente se rinde, ¿el trabajo que se estaba haciendo en su
  nombre se detiene, o sigue corriendo para nadie?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

```
hedged requests  -> tras un umbral, dispara una copia a otra replica
tied requests    -> dispara ambas copias desde el inicio, cancela la
                     perdedora con una señal rapida entre replicas

deadline propagation    -> pasa el presupuesto de tiempo RESTANTE por
                            toda la cadena de llamadas
cancelacion propagada   -> detiene el trabajo del lado del servidor en
                            cuanto el cliente se rinde, en toda la cadena
```

Los primeros dos (hedged, tied) atacan la cola desde el lado del
**cliente**: como conseguir la respuesta mas rapida posible, aceptando
algo de trabajo redundante a cambio. Los ultimos dos (deadline,
cancelacion) atacan el problema desde el lado del **sistema**: como
evitar que el tiempo y el trabajo se desperdicien en algo que ya no le
sirve a nadie.

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-hedged-requests](1-hedged-requests) | Del paper "The Tail at Scale": tras un umbral, dispara una copia a otra replica y toma la que responda primero — cuantifica el tradeoff entre umbral, carga extra y mejora de cola. |
| 2 | [2-tied-requests](2-tied-requests) | Variante donde ambas replicas arrancan a la vez y se cancelan mutuamente — mejor que hedging cuando la latencia viene de colas de trabajo, no de ejecucion lenta. |
| 3 | [3-deadline-propagation](3-deadline-propagation) | Pasar el presupuesto de latencia restante por toda la cadena de llamadas, en vez de que cada capa aplique su propio timeout fijo. |
| 4 | [4-cancelacion-propagada](4-cancelacion-propagada) | Liberar el trabajo del servidor en cuanto el cliente se rinde — sin esto, un incidente breve puede generar una recuperacion 20 veces mas larga. |

## Orden de lectura sugerido

`1 -> 2 -> 3 -> 4`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
