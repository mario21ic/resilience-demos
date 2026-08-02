# 3. Backoff exponencial

## Que es

El **backoff exponencial** es la estrategia que decide cuanto esperar
entre un intento y el siguiente cuando se reintenta una operacion
(ver [2-retry](../2-retry)): la espera crece exponencialmente con el
numero de intento en vez de mantenerse constante.

```
delay(intento) = min(max_delay, base * factor ^ (intento - 1))
```

Con `base=0.5s` y `factor=2`: `0.5s, 1s, 2s, 4s, 8s, 16s, ...` hasta
un `max_delay` que acota el crecimiento (sin tope, unos pocos
intentos ya estarian esperando minutos u horas).

Este ejemplo profundiza especificamente en el algoritmo de backoff en
si (independiente de hacer la llamada de red), y en por que el
backoff exponencial "puro" no alcanza: hace falta **jitter**.

## El problema que el backoff puro no resuelve: thundering herd

El backoff exponencial puro es **determinista**: para el mismo numero
de intento, todos los clientes calculan exactamente la misma espera.

Si muchos clientes fallan al mismo tiempo (por ejemplo, una
dependencia compartida se reinicia y corta todas las conexiones
activas), **todos** programan su reintento para el mismo instante.
El resultado es una rafaga sincronizada de requests -"thundering
herd"- justo cuando el servicio recien esta volviendo a estar
disponible, lo que puede tumbarlo de nuevo.

## La solucion: jitter

Se le agrega aleatoriedad a la espera calculada para dispersar los
reintentos en el tiempo. Este ejemplo implementa las tres variantes
descritas en el articulo "Exponential Backoff and Jitter" de AWS:

- **Full jitter**: `random(0, cap)`. Maxima dispersion; algunos
  clientes reintentan casi de inmediato, otros esperan cerca del tope.
- **Equal jitter**: `cap/2 + random(0, cap/2)`. Menos dispersion que
  full jitter, pero garantiza una espera minima.
- **Decorrelated jitter**: `random(base, prev_delay * 3)`, acotado a
  `max_delay`. No depende del numero de intento sino de la espera
  anterior; en la practica dispersa aun mas que full jitter
  manteniendo una tendencia creciente.

## Estructura del ejemplo

- `backoff.py`: las cuatro funciones de calculo de delay
  (`exponential_delay`, `full_jitter`, `equal_jitter`,
  `decorrelated_jitter`), sin ninguna llamada de red — puro calculo,
  facil de probar y comparar de forma aislada.
- `demo_backoff.py`:
  1. Imprime una tabla con el delay por intento (1 a 8) para cada
     estrategia, mostrando el crecimiento exponencial y el tope.
  2. Simula 24 clientes que fallan a la vez (t=0) y calculan su
     reintento del intento #1 bajo tres estrategias, mostrando un
     histograma ASCII de en que instante caeria cada reintento.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_backoff.py
```

Salida esperada (semilla fija para reproducibilidad):

```
Sin jitter (backoff exponencial puro) -> thundering herd:
   0.00- 0.20s |  (0)
   0.20- 0.40s |  (0)
   0.40- 0.60s | ######################## (24)

Con full jitter -> reintentos dispersos en el tiempo:
   0.00- 0.20s | ############# (13)
   0.20- 0.40s | ####### (7)
   0.40- 0.60s | #### (4)
```

Los 24 reintentos "sin jitter" caen en un unico bucket (misma espera
para todos). Con jitter, la carga se reparte en varios buckets,
reduciendo el pico de requests simultaneos.

## Puntos clave

- Backoff exponencial resuelve "no insistir al mismo ritmo"; jitter
  resuelve "no insistir todos juntos". Son complementarios, no
  alternativas.
- Siempre acotar el delay con un `max_delay`: el crecimiento
  exponencial sin tope es impractico despues de pocos intentos.
- Full jitter maximiza la dispersion (mejor para mitigar thundering
  herd); equal/decorrelated jitter son utiles cuando se quiere
  garantizar una espera minima antes de reintentar.
- Este calculo de delay es el que se conecta con el bucle de retry de
  [2-retry](../2-retry) — aqui se aisla para poder razonar sobre el
  algoritmo sin la complejidad de la llamada de red.
