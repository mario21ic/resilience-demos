# Consumidor idempotente / deduplicación

## Que es

Ningun broker de mensajes real ofrece *exactly-once* a nivel de
entrega. Lo que ofrecen es **at-least-once** (puede reentregar un
mensaje ya procesado: un ack que se perdio en la red, un consumidor
que se cayo justo despues de procesar pero antes de confirmar) o
*at-most-once* (puede perder mensajes, pero nunca duplicarlos).
"Exactly-once" como experiencia solo se logra combinando
at-least-once con un consumidor **idempotente**: no importa cuantas
veces llegue el mismo mensaje, el efecto final tiene que ser como si
hubiera llegado una sola vez.

Es la otra mitad del problema que resuelve el
[transactional outbox](../2-transactional-outbox-inbox) del lado del
productor — outbox garantiza que el evento se publica al menos una
vez; este ejemplo cubre que hacer del lado del consumidor para que
"al menos una vez" no se convierta en "aplicado mas de una vez".

## Tres formas de lograrlo

1. **Nada**: si la operacion no es idempotente por naturaleza (sumar
   un delta, incrementar un contador) y no hay deduplicacion, cada
   redelivery duplica el efecto de negocio. Sin excepciones.
2. **Deduplicacion con ventana (TTL)**: recordar los IDs de mensajes
   procesados recientemente, con vencimiento — barato de mantener
   (una cache en memoria), pero solo protege DENTRO de la ventana.
   Una redelivery que llega despues de que la entrada vencio se trata
   como si fuera nueva.
3. **Idempotencia natural**: redisenar la operacion misma para que
   aplicarla dos veces con el mismo mensaje de el mismo resultado —
   no hace falta recordar nada, la garantia es estructural.

## Cuanto se cuela con una ventana finita

Las demoras de redelivery en un sistema real no son uniformes: la
gran mayoria ocurre en segundos, pero una fraccion chica puede tardar
horas o dias (un consumidor caido por mantenimiento, un mensaje
reprocesado desde una
[dead letter queue](../4-dead-letter-queue) mucho despues). Este
ejemplo cuantifica, contra esa distribucion realista, que fraccion de
duplicados se sigue aplicando dos veces segun el tamaño de la
ventana de deduplicacion.

## Estructura del ejemplo

- `dedup.py`: `NonIdempotentAccount` (el problema), `TTLDedupCache`
  (deduplicacion con ventana), `NaturallyIdempotentAccount`
  (idempotencia por construccion), `draw_redelivery_delay` (la
  distribucion realista de demoras).
- `demo_dedup.py`: tres partes.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_dedup.py
```

Salida esperada:

```
Parte 1: segunda entrega -> saldo: 100.0 (deberia seguir siendo 50)

Parte 2:
     ventana | duplicados atrapados | igual se aplican 2 veces
       1 min |              98.00% |                  1.995%
      1 hora |              98.07% |                  1.927%
       1 dia |             100.00% |                  0.000%

Parte 3: redelivery de la MISMA version -> saldo: 50.0 (sin cambios)
```

Incluso una ventana de una hora — generosa para la mayoria de los
sistemas — deja pasar casi un 2% de duplicados, porque la cola de
demoras de redelivery no tiene un limite practico de mantener en
memoria.

## Puntos clave

- Preferir operaciones **naturalmente idempotentes** (upserts, "fijar
  el valor final" en vez de "incrementar", claves de version) elimina
  la necesidad de infraestructura de deduplicacion — es la solucion
  mas robusta cuando el modelo de negocio lo permite.
- Cuando no es posible (la operacion es intrinsecamente un delta, como
  "cobrar $50 mas"), una ventana de deduplicacion reduce el problema
  pero no lo elimina — para eliminarlo hace falta persistencia
  permanente (la tabla `inbox` del ejemplo anterior).
- El tamaño de la ventana es un tradeoff explicito entre costo
  (memoria, tiempo de vida de la cache) y cuanto tiempo de cola larga
  se esta dispuesto a tolerar — no hay un valor "correcto" universal,
  depende de cuanto puede tardar una redelivery en el peor caso real
  del sistema.
- Esto es el mismo principio que las
  [idempotency keys](../../level1/7-idempotency-keys) de level1, pero
  aplicado a mensajes entregados por un broker en vez de a reintentos
  de un cliente HTTP — la clave de idempotencia, en ambos casos, es
  quien permite distinguir "esto ya paso" de "esto es nuevo".
