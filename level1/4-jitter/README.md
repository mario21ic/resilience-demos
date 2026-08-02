# 4. Jitter

## Que es

El **jitter** es aleatoriedad agregada al calculo de backoff (ver
[3-backoff-exp](../3-backoff-exp)) para que clientes que fallan al
mismo tiempo no reintenten todos en el mismo instante.

El backoff exponencial puro define un **tope** de espera que crece
con el numero de intento, pero es determinista: mismo intento, mismo
numero, para todos los clientes. El jitter decide *como* elegir un
valor dentro (o alrededor) de ese tope.

Este ejemplo compara las tres variantes del articulo "Exponential
Backoff and Jitter" (AWS Architecture Blog):

| Variante | Formula | Rango resultante |
|---|---|---|
| **Full jitter** | `uniform(0, cap)` | `[0, cap]` |
| **Equal jitter** | `cap/2 + uniform(0, cap/2)` | `[cap/2, cap]` |
| **Decorrelated jitter** | `uniform(base, prev_delay * 3)`, acotado | crece con la espera anterior, no con el intento |

## Estructura del ejemplo

- `jitter.py`: las tres funciones de jitter mas `exponential_cap`
  (el tope determinista del que dependen full jitter y equal jitter).
- `demo_jitter.py`: dos comparaciones independientes.

### Parte 1 — forma de la distribucion

Para un mismo intento (cap determinista = 8s), se toman 5000 muestras
de cada variante y se calcula min/max/media/desviacion, mas un
histograma ASCII. Esto muestra visualmente:

- **Full jitter**: uniforme en todo `[0, cap]` — la mayor dispersion
  posible, media = `cap/2`, pero permite reintentos casi inmediatos.
- **Equal jitter**: uniforme en `[cap/2, cap]` — misma amplitud de
  rango que full jitter dividida a la mitad, pero con un piso
  garantizado (nunca reintenta antes de `cap/2`).
- **Decorrelated jitter**: rango `[base, prev*3]`, que no esta atado
  al numero de intento sino a la ultima espera usada; en la practica
  termina cubriendo un rango mas amplio que las otras dos.

### Parte 2 — simulacion de recuperacion con capacidad limitada

Se simulan 100 clientes que fallan exactamente al mismo tiempo (por
ejemplo, una dependencia se reinicio y corto todas las conexiones)
contra un servidor que solo puede aceptar 8 requests por ventana de
0.5s. Cada cliente reintenta segun la estrategia asignada hasta tener
exito. Se mide, por estrategia:

- **Tiempo total** hasta que el ultimo cliente logra conectarse.
- **Llamadas totales** generadas contra el servidor (incluye las
  fallidas).

Esto cuantifica el impacto real del thundering herd: sin jitter,
todos los clientes que fallan juntos vuelven a colisionar juntos en
cada ronda (mismo intento -> misma espera), asi que el servidor solo
puede "pelar" 8 por ronda del bloque completo. Con jitter, el bloque
se dispersa en el tiempo y deja de competir todo contra si mismo.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_jitter.py
```

Salida esperada de la parte de simulacion (semilla fija, `42`):

```
            estrategia | tiempo total |  llamadas totales | abandonados
------------------------------------------------------------------------
            sin_jitter |      218.00s |               676 |           0
           full_jitter |       18.50s |               392 |           0
          equal_jitter |       15.50s |               432 |           0
   decorrelated_jitter |       10.00s |               307 |           0
```

La diferencia es enorme: **sin jitter tarda ~20x mas** en drenar el
mismo bloque de 100 clientes que cualquiera de las variantes con
jitter, porque siguen colisionando en bloque ronda tras ronda.

## Puntos clave

- Full jitter maximiza la dispersion (mejor caso general segun el
  benchmark de AWS), pero puede generar reintentos casi inmediatos.
- Equal jitter sacrifica algo de dispersion a cambio de garantizar una
  espera minima antes de cada reintento.
- Decorrelated jitter no depende del numero de intento sino de la
  espera anterior; en este demo es la que menos llamadas totales y
  menor tiempo de recuperacion produce.
- No hay una variante "correcta" universal: la eleccion depende de si
  se prioriza dispersion maxima, una espera minima garantizada, o
  simplicidad de implementacion (full jitter es la mas simple de las
  tres).
- El jitter no reemplaza al backoff exponencial ni al limite de
  intentos de [2-retry](../2-retry): son piezas del mismo mecanismo,
  no alternativas entre si.
