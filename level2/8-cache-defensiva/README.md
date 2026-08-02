# 8. Cache defensiva

## Que es

Un cache "ingenuo" — guardar un valor con un TTL, recalcularlo al
vencer — tiene tres puntos ciegos comunes. Este ejemplo implementa una
tecnica para cada uno:

1. **Stale-while-revalidate**: al vencer, no bloquear al llamador
   mientras se refresca — servirle el valor viejo de inmediato y
   refrescar en background.
2. **Negative caching**: cachear tambien los "no existe", no solo los
   valores encontrados.
3. **Expiracion probabilistica temprana** (XFetch): evitar que todos
   los lectores detecten el vencimiento en el mismo instante exacto.

Las tres reducen carga sobre el backend sin sacrificar correctitud —
es la misma familia de ideas que
[request coalescing](../7-request-coalescing), aplicada dentro del
cache en vez de en la capa de llamadas.

## 1) Stale-while-revalidate

Un cache comun, al vencer el TTL, bloquea al llamador hasta terminar
de recalcular el valor. Con stale-while-revalidate, se le devuelve el
valor VIEJO de inmediato (dentro de una ventana de "viejo pero
utilizable", `stale_ttl`) mientras UN solo refresco en background lo
actualiza — sin importar cuantos lectores encuentren el valor stale al
mismo tiempo, solo se dispara un refresco.

```
SWRCache(ttl=0.3, stale_ttl=1.0)

  1) cache vacio            -> bloquea 0.3s (no hay nada que servir)
  2) inmediatamente despues -> fresh, instantaneo
  3) recien vencido         -> stale, instantaneo + dispara refresh en background
  4) otro lector, stale     -> stale, instantaneo, NO dispara un segundo refresh
  5) tras terminar el refresh -> fresh de nuevo, con el valor actualizado
```

## 2) Negative caching

Si una clave no existe, buscarla puede costar tanto como encontrarla
(un scan, una consulta que no matchea nada). Sin cachear ese
resultado, cada lookup repetido vuelve a pagar ese costo. La clave es
usar un TTL **mas corto** para las entradas negativas que para las
positivas: lo suficiente para no volver a preguntar en el corto plazo,
pero sin arriesgarse a creer "no existe" por mucho tiempo si el
recurso aparece despues.

## 3) Expiracion probabilistica temprana (XFetch)

Si muchos lectores comparten una clave que esta por vencer, todos
detectan el vencimiento en el mismo instante exacto y todos
recalculan a la vez — un cache stampede (el mismo problema que
resuelve [7-request-coalescing](../7-request-coalescing), pero visto
desde el cache en vez de desde el llamador).

La formula de XFetch (paper "Optimal Probabilistic Cache Stampede
Prevention", Vattani et al.) le da a cada lectura, a medida que se
acerca el vencimiento, una probabilidad creciente de refrescar un
poco ANTES — para que sea uno solo el que dispare el refresco
temprano, en un momento distinto para cada uno, en vez de todos juntos
exactamente al vencer:

```
should_refresh_early(now, expires_at, delta, beta):
    return now - delta * beta * log(random()) >= expires_at
```

`delta` es cuanto cuesta recalcular el valor: cuanto mas caro, mayor
la anticipacion util.

## Estructura del ejemplo

- `defensive_cache.py`: `SWRCache`, `CacheWithNegativeEntries` y
  `should_refresh_early`, las tres tecnicas de forma independiente.
- `demo_cache_defensiva.py`: tres partes, una por tecnica, cada una
  con su propio backend simulado y su propia comparacion antes/despues.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_cache_defensiva.py
```

Salida esperada (resumen; Parte 3 usa una semilla fija):

```
Parte 1: llamadas reales a slow_fetch(): 2 (una por el miss inicial, una por el refresh)
         ningun llamador esperó los 0.3s del fetch, salvo el primero.

Parte 2: sin negative caching: 5/5 llamadas reales
         con negative caching: 1/5 llamadas reales

Parte 3: dispararon ANTES del vencimiento exacto: 1552/3000 (51.7%)
         llegaron sin disparar hasta el vencimiento exacto: 1448/3000 (48.3%)
```

Con `delta=0.05s` (recomputar es barato) solo un poco mas de la mitad
dispara temprano; subiendo `delta` a `0.3s` (recomputar es mas caro)
ese numero sube a ~100% — es la perilla que se ajusta segun cuanto
cueste recalcular el valor real.

## Puntos clave

- Las tres tecnicas atacan el mismo objetivo (menos carga sobre el
  backend) desde angulos distintos, y se combinan sin conflicto entre
  si: nada impide un `SWRCache` que ademas cachee negativos y use
  expiracion probabilistica para decidir cuando arrancar el refresh
  en background.
- Stale-while-revalidate cambia "el llamador espera" por "el llamador
  recibe un dato levemente viejo" — valido para datos que toleran
  algo de staleness (casi todo lo que no sea un balance de cuenta o un
  inventario exacto).
- Negative caching evita un anti-patron comun (tratar un "no
  encontrado" como si no costara nada cachear) sin caer en el
  opuesto (cachearlo para siempre y no enterarse nunca de que el
  recurso ya existe).
- La expiracion probabilistica complementa, no reemplaza, al
  [request coalescing](../7-request-coalescing): incluso si alguien
  dispara un refresco temprano, sigue siendo valioso que solo un
  refresco real este en vuelo a la vez para esa clave.
