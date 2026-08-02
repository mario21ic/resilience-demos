# 3. Backoff exponencial con topes (capped / truncated)

## Que es

El backoff exponencial hace crecer la espera entre reintentos con
cada intento fallido:

```
raw_delay(intento) = base * factor ^ (intento - 1)
```

Sin ningun limite, esto se va de control muy rapido: con
`base=0.1s, factor=2`, el intento 20 ya espera **~14.6 horas**. Este
ejemplo se enfoca puntualmente en como evitar eso — **no** trata sobre
jitter (aleatoriedad), eso se ve por separado en
[4-jitter](../4-jitter). Aca el problema es mas basico: como acotar el
crecimiento exponencial en si, antes de pensar en dispersion.

Se comparan dos formas de ponerle techo, mas un tercer concepto que
suele pasarse por alto: capar el delay por intento no es lo mismo que
capar el tiempo total que un llamador esta dispuesto a esperar.

## Las dos formas de topar el crecimiento

- **Capped (delay capado)**: `min(max_delay, raw_delay(intento))`. El
  exponente sigue creciendo libremente, pero el resultado final se
  recorta a un valor maximo elegido de antemano. Es la variante mas
  comun en la practica (SDKs de AWS, clientes HTTP, gRPC): simple, un
  solo parametro controla el peor caso.

- **Truncated (exponente truncado)**: a partir de un numero fijo de
  intentos (`max_growth_attempts`), el EXPONENTE deja de crecer, asi
  que el delay se estabiliza en ese valor — no en un numero de
  politica elegido a mano, sino en el que sale de evaluar la propia
  formula en ese punto. Es el termino clasico del algoritmo CSMA/CD de
  Ethernet (IEEE 802.3): "truncated binary exponential backoff".

La diferencia practica: `truncated` tipicamente se estabiliza **antes
y en un valor mas bajo** que un `capped` con un techo generico,
porque el punto de corte se elige en funcion de cuantos intentos de
crecimiento tienen sentido, no de un limite absoluto arbitrario.

## El tercer concepto: presupuesto de tiempo total (deadline)

Capar el delay de CADA intento no evita que la SUMA de todas las
esperas supere el tiempo que el llamador realmente tiene disponible
(por ejemplo, el timeout total de un request HTTP entrante, o un
deadline propagado entre servicios). Son dos mecanismos distintos:

- El cap **por intento** acota cuanto se espera de una vez.
- El **presupuesto total** acota cuanto tiempo acumulado se le puede
  dedicar a reintentar antes de rendirse, sin importar si cada espera
  individual era "legal".

## Estructura del ejemplo

- `backoff.py`: `uncapped`, `capped` y `truncated`, documentadas con
  la diferencia conceptual entre ellas.
- `demo_backoff.py`:
  1. Tabla de crecimiento (intentos 1-20) comparando las tres
     variantes, mostrando como `uncapped` escala a horas mientras las
     otras dos se estabilizan.
  2. Simulacion de un presupuesto de tiempo total de 20s, mostrando
     cuantos intentos caben con `capped` vs con `truncated` antes de
     que el PROXIMO delay superaria el presupuesto.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_backoff.py
```

Salida esperada (resumen):

```
intento |     uncapped |  capped (max=30s) |  truncated (N=5, max=60s)
      9 |        25.6s |             25.6s |                      1.6s
     10 |        51.2s |             30.0s |                      1.6s
     20 |        14.6h |             30.0s |                      1.6s
```

```
Con 'capped' (max_delay=30s): 7 intentos completados, 12.70s consumidos
Con 'truncated' (N=5, max_delay=60s): 15 intentos completados, 19.10s consumidos
```

Con el mismo presupuesto de 20s, `truncated` permite mas del doble de
intentos que `capped`, porque su plateau (1.6s) es mucho mas bajo que
el techo generico de 30s.

## Puntos clave

- Backoff exponencial **sin tope** no es una opcion viable: en pocos
  intentos el delay deja de tener sentido practico.
- `capped` es simple y suficiente cuando el objetivo es solo evitar
  esperas absurdas; `truncated` da mas control fino sobre cuantos
  intentos "rapidos" se quieren permitir antes de plancharse en un
  valor bajo.
- Un cap por intento **no reemplaza** un presupuesto de tiempo total:
  si el llamador tiene un deadline, hay que chequear tiempo acumulado
  contra ese deadline, no solo el delay de cada intento por separado.
- Esto es ortogonal al jitter ([4-jitter](../4-jitter)): primero se
  decide como topar el crecimiento (este ejemplo), despues se decide
  si agregarle aleatoriedad al valor ya topado.
