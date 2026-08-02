# 6. Backpressure

## Que es

El [load shedding](../5-load-shedding) y el
[throttling](../4-throttling) son decisiones **unilaterales** de quien
recibe el trabajo: rechazar o demorar, sin que el productor
necesariamente se entere ni cambie su comportamiento. El
**backpressure** es distinto: es una señal que viaja hacia **atras**
en la cadena, del consumidor hacia el productor, para que el
productor mismo reduzca su ritmo — cooperacion entre las dos puntas,
no una decision unilateral de una sola.

La forma mas simple y universal de backpressure es una **cola
acotada**: si el productor intenta agregar un item y la cola ya esta
llena, la operacion de encolar **bloquea** hasta que el consumidor
libere lugar. Ese bloqueo es la señal en si misma — el productor no
puede avanzar mas rapido de lo que el consumidor retira trabajo. Es el
mismo principio detras de la ventana deslizante de TCP, de los
`BlockingQueue` de Java, de los canales con buffer limitado de Go, o
del `highWaterMark` de los streams de Node.js.

## Estructura del ejemplo

- `pipeline.py`: `run_pipeline(q, n_items, produce_interval, consume_interval)`
  corre un productor rapido y un consumidor lento sobre la cola que se
  le pase, y devuelve metricas: cuando termino de producir, cuando
  termino de consumir, el tamaño maximo que alcanzo la cola, y una
  serie de muestras en el tiempo.
- `demo_backpressure.py`: dos partes.
  1. Corre el mismo productor/consumidor sobre una `queue.Queue()`
     **sin limite** vs. una `queue.Queue(maxsize=5)` — mostrando que
     lo que cambia no es solo el tamaño de la cola, sino el **ritmo
     del productor**.
  2. La variante "pull" del mismo problema con un generador: el
     productor no puede adelantarse porque su codigo literalmente no
     corre hasta que el consumidor le pide el siguiente valor.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_backpressure.py
```

Salida esperada (productor cada 10ms, consumidor cada 80ms, 40 items;
los tiempos exactos pueden variar levemente por el scheduling real):

```
Escenario 1: cola SIN limite (sin backpressure)
  -> productor termino en 0.48s, consumidor termino en 3.33s, tamano maximo de cola: 32

Escenario 2: cola CON limite de 5 (con backpressure)
  -> productor termino en 2.86s, consumidor termino en 3.34s, tamano maximo de cola: 5
```

Sin backpressure, el productor **no se entera de nada**: termina su
trabajo en 0.48s (su ritmo nativo) y deja una cola de hasta 32 items
pendientes, que el consumidor recien termina de drenar 3 segundos
despues. Con backpressure, el productor tarda 2.86s en terminar —
practicamente lo mismo que el consumidor— porque el propio `put()` lo
frena en cuanto la cola llega a su limite de 5.

## Puntos clave

- Backpressure es **flujo de control cooperativo**: el productor
  cambia su comportamiento porque el consumidor se lo hace sentir, no
  porque alguien le avise explicitamente con un mensaje de error.
- El costo de no tener backpressure no es solo memoria (una cola que
  crece sin limite): es tambien latencia — el ultimo item de una cola
  de 32 espera muchisimo mas que el primero, y esa espera crece con
  cada nuevo item que el productor sigue agregando sin saber que hay
  un cuello de botella atras.
- Una cola acotada es la forma mas simple de backpressure porque no
  requiere que el productor ni el consumidor sepan nada especial del
  otro — el bloqueo en `put()` alcanza. La variante "pull" (Parte 2)
  es aun mas directa cuando se puede: el productor no necesita ni
  saber que existe backpressure, simplemente nunca corre por
  adelantado.
- Backpressure funciona mejor entre componentes que **ambos
  controlas** (dos servicios propios, un pipeline interno). Contra un
  cliente externo que no coopera, las herramientas correctas son
  [rate limiting](../3-rate-limiting) o
  [load shedding](../5-load-shedding): ahi no hay forma de "bloquear"
  a alguien que no esta escuchando la señal.
