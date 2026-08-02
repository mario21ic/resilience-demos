# 5. Load shedding

## Que es

El [throttling](../4-throttling) encola el exceso de trafico y lo
demora. El **load shedding** no encola nada: cuando el sistema esta
cerca de su capacidad, decide **en el acto** si admite o rechaza cada
request — y lo hace teniendo en cuenta su **prioridad**, para que, si
hay que sacrificar trafico, se sacrifique primero el menos importante.

Es la misma idea de un bote salvavidas con lugares limitados:
priorizar quien sube primero, no importa el orden en que llegaron a la
cubierta. Este ejemplo sigue la terminologia del libro de SRE de
Google (capitulo "Handling Overload"): clases de criticidad como
`CRITICAL`, `DEFAULT` y `SHEDDABLE`, simplificadas aca a esas tres.

## Por que el orden de llegada no alcanza

Un shedder ingenuo simplemente admite hasta llenar la capacidad
(FIFO) y rechaza el resto, sin mirar que es cada request. El problema:
trafico de fondo poco importante (batch, prefetch, analytics) puede
llegar ANTES que trafico critico (un pago, un login) simplemente por
timing, y quedarse con toda la capacidad — dejando al trafico
importante sin lugar cuando mas se lo necesita.

## La solucion: umbrales de utilizacion por prioridad

En vez de un unico limite de capacidad, cada prioridad tiene su propio
umbral de utilizacion a partir del cual se le empieza a rechazar:

| Prioridad | Se rechaza a partir de |
|---|---|
| `sheddable` | 50% de uso |
| `default` | 80% de uso |
| `critical` | 100% de uso |

Cuanto mas importante la prioridad, mas tarde empieza a sufrir
rechazos — el margen entre umbrales queda reservado, implicitamente,
para lo que todavia no llego pero puede ser mas importante.

## Estructura del ejemplo

- `load_shedder.py`: `LoadShedder.try_admit(priority)` compara la
  utilizacion actual (`in_flight / capacity`) contra el umbral de esa
  prioridad; admite y suma un cupo, o rechaza sin esperar nada.
- `server.py`: endpoint `GET /api/work?priority=critical|default|sheddable`
  que ocupa un cupo, "trabaja" 1 segundo y lo libera; responde `503`
  de inmediato si no consigue cupo.
- `client_load_shedding.py`: aplica la misma secuencia de llegada —
  7 `sheddable`, despues 6 `default`, recien al final 4 `critical`—
  contra dos shedders (sin y con prioridad), y despues valida el mismo
  comportamiento contra el endpoint HTTP real.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_load_shedding.py
```

Salida esperada (capacidad=10, misma secuencia en ambos casos):

```
 prioridad |     sin prioridad (FIFO) |   con prioridad (shedding por clase)
 sheddable |            7/7 admitidos |                        5/7 admitidos
   default |            3/6 admitidos |                        3/6 admitidos
  critical |            0/4 admitidos |                        2/4 admitidos
```

Sin prioridad, `critical` queda en **0% de exito** solo por haber
llegado despues de que `sheddable` y `default` ya llenaron la
capacidad. Con prioridad, `sheddable` cede un poco de su lugar (de
100% a 71% de exito) y eso alcanza para que `critical` pase de 0% a
50% de exito — la Parte 2 confirma exactamente estos mismos numeros
contra el servidor HTTP real.

## Puntos clave

- Load shedding rechaza **inmediatamente**, sin cola ni espera — es la
  herramienta para cuando ni siquiera vale la pena demorar el
  trabajo, porque el sistema ya esta al limite de lo que puede
  procesar en curso.
- La prioridad no es solo "orden de llegada" — es una propiedad del
  request que el sistema debe conocer de antemano (un header, un
  campo del payload, el tipo de cliente) para poder actuar en
  consecuencia.
- Reservar margen para las prioridades altas tiene un costo real: las
  prioridades bajas pierden exito que, en un esquema FIFO, hubieran
  tenido. Es una decision explicita de que trafico importa mas cuando
  no alcanza para todos.
- Se combina bien con [circuit breaker](../1-circuit-breaker) y
  [bulkhead](../2-bulkhead): el circuit breaker decide si seguir
  llamando a una dependencia degradada, el bulkhead aisla cuanto
  puede consumir cada dependencia, y el load shedding decide, dentro
  de la capacidad propia del sistema, a quien atender primero cuando
  no alcanza para todos.
