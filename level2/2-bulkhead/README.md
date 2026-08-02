# 2. Bulkhead

## Que es

El [circuit breaker](../1-circuit-breaker) protege a la **dependencia**
de seguir recibiendo trafico cuando esta degradada. El **bulkhead**
resuelve un problema distinto: protege al **cliente** de si mismo,
cuando varias dependencias sin relacion entre si terminan compitiendo
por los mismos recursos limitados (threads, conexiones, colas) del
lado de quien las llama.

El nombre viene de los mamparos (*bulkheads*) que dividen el casco de
un barco en compartimentos estancos: si uno se inunda, el agua no pasa
a los demas y el barco no se hunde entero. Aplicado a software: si una
dependencia se degrada y consume todos los recursos que tiene
asignados, eso no deberia poder afectar las llamadas a **otras**
dependencias que comparten el mismo proceso.

## El problema: un pool compartido propaga la falla

Supongamos que una app llama a `service_a` y a `service_b`, dos
servicios sin ninguna relacion entre si. Si ambas llamadas comparten
el mismo pool de recursos del lado del cliente (el mismo pool de
threads, el mismo pool de conexiones HTTP) y `service_a` se pone
lenta, cada llamada a A ocupa un lugar del pool durante mas tiempo.
Eventualmente el pool se llena de llamadas a A, y las llamadas a B
—que en si misma sigue perfectamente sana— tambien empiezan a
fallar, simplemente porque no consiguen un lugar libre.

Un problema de A termina tumbando a B sin que exista **ninguna razon
tecnica** para que eso pase, mas alla de compartir el mismo pool. Esto
se conoce como el problema del "vecino ruidoso" (*noisy neighbor*).

## La solucion: un pool por dependencia

El bulkhead le da a cada dependencia su **propio** pool aislado — en
este ejemplo, un semaforo con limite propio (`Bulkhead`). Si A se
degrada, su pool se satura y algunas llamadas a A se rechazan de
inmediato (fail fast) — pero el pool de B ni se entera: B sigue
teniendo toda su capacidad disponible.

## Estructura del ejemplo

- `bulkhead.py`: la clase `Bulkhead`, un semaforo no bloqueante —
  `call(func)` ejecuta `func` si hay lugar, o lanza
  `BulkheadFullError` de inmediato si el pool ya esta al limite (sin
  encolar: una cola sin limite es en si misma un problema).
- `server.py`: dos dependencias simuladas sin relacion entre si —
  `service-a` (comportamiento configurable) y `service-b` (siempre
  sana y rapida).
- `client_bulkhead.py`: lanza una rafaga de 12 llamadas concurrentes a
  `service_a` (lenta) y 4 a `service_b` (sana), y compara:
  1. **Escenario 1**: A y B comparten un unico `Bulkhead` (pool
     compartido, capacidad 4).
  2. **Escenario 2**: A y B tienen cada uno su propio `Bulkhead`
     (pools aislados: A con capacidad 2, B con capacidad 4).

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_bulkhead.py
```

Salida esperada:

```
Escenario 1: SIN bulkhead — service_a y service_b comparten un pool de 4
  service_a: 12 llamadas -> 4 exitosas, 8 rechazadas por bulkhead lleno
  service_b: 4 llamadas -> 0 exitosas, 4 rechazadas por bulkhead lleno

Escenario 2: CON bulkhead — cada servicio tiene su propio pool aislado
  service_a: 12 llamadas -> 2 exitosas, 10 rechazadas por bulkhead lleno
  service_b: 4 llamadas -> 4 exitosas, 0 rechazadas por bulkhead lleno
```

En el escenario 1, `service_b` pierde el 100% de sus llamadas sin
tener ningun problema propio, solo por compartir pool con `service_a`.
En el escenario 2, `service_b` tiene exito el 100% de las veces —
`service_a` sigue tan lento como antes y absorbe sus propios rechazos,
pero eso queda completamente contenido en su propio compartimento.

## Puntos clave

- El bulkhead no evita que una dependencia se degrade — evita que su
  degradacion se **propague** a dependencias que no tienen nada que
  ver.
- Rechazar de inmediato (fail fast) cuando el pool esta lleno es
  preferible a encolar sin limite: una cola ilimitada solo demora el
  problema y agrega presion de memoria y latencia acumulada.
- El tamano de cada pool es una decision explicita de capacidad: darle
  a una dependencia poco confiable un pool chico limita el dano que
  puede causar, sin necesidad de saber de antemano cuando se va a
  degradar.
- Bulkhead y [circuit breaker](../1-circuit-breaker) resuelven
  problemas complementarios: el circuit breaker decide si vale la pena
  seguir llamando a UNA dependencia degradada; el bulkhead decide
  cuanto puede consumir esa dependencia de los recursos compartidos
  del cliente, incluso mientras el circuito sigue cerrado.
