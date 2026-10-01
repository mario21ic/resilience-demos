# Observabilidad: RED, USE, trazas distribuidas, histogramas

## Que es

Cuatro ideas practicas para saber que esta pasando en un sistema
distribuido, mas alla de "¿esta prendido?":

- **RED** (Rate, Errors, Duration): las tres metricas para cualquier
  cosa que atiende requests. Son indicadores **tardios**: solo se
  mueven una vez que un problema ya esta afectando trafico real.
- **USE** (Utilization, Saturation, Errors): las tres metricas para
  cualquier **recurso** (CPU, disco, una cola). La saturacion es un
  indicador **temprano**: un recurso puede saturarse mucho antes de
  que eso se traduzca en errores o latencia real para los clientes.
- **Trazas distribuidas**: seguir un unico request a traves de varios
  servicios para saber DONDE se fue el tiempo, no solo cuanto tardo
  en total.
- **Histogramas, no promedios**: un promedio es un solo numero que
  puede esconder una realidad bimodal.

## Por que un promedio miente

Un promedio comprime toda una distribucion en un solo numero — y ese
numero puede verse perfectamente razonable mientras una fraccion real
de los usuarios tiene una experiencia pesima. Peor todavia: promediar
promedios YA calculados por host, sin ponderar por cuanto trafico
manejo cada uno, puede exagerar (o esconder) la realidad por un
factor enorme. La correccion es simple pero poco practicada:
reportar percentiles (p50, p95, p99) sobre el conjunto completo de
mediciones individuales, nunca un promedio de promedios.

## Por que USE avisa antes que RED

Un recurso compartido (una cola, un pool de conexiones) puede
saturarse progresivamente sin que eso todavia se note en las metricas
de request (RED) — los requests siguen teniendo exito, hasta que el
recurso se desborda del todo. Monitorear la saturacion da una ventana
de tiempo real para actuar (escalar, aplicar
[load shedding](../../level2/5-load-shedding)) antes de que el
problema le llegue a un solo usuario.

## Estructura del ejemplo

- `observability.py`: `percentile` y `simulate_saturation_vs_errors`.
- `demo_observability.py`: tres partes.
  1. Una latencia bimodal que el promedio esconde, mas la trampa del
     promedio de promedios.
  2. Cuantos ticks de aviso previo da la saturacion (USE) antes de
     que aparezcan errores reales (RED).
  3. Un desglose de traza que revela donde se fue el 92% del tiempo
     de un request.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_observability.py
```

Salida esperada:

```
Parte 1: promedio=109.5ms (parece bien), pero p95=2000ms (5% de los requests)
         promedio de promedios sin ponderar: 255ms vs promedio real: 15.4ms (16.6x de error)

Parte 2: saturacion cruza 80% en el tick 39; errores reales recien en el tick 49
         -> 10 ticks de aviso previo

Parte 3: 92% del tiempo total esta en un solo salto (la base de datos)
```

## Puntos clave

- Nunca reportar solo un promedio de latencia — como minimo, p50 y
  p99 juntos. La misma logica que ya aparecio en
  [hedged requests](../../level4/1-hedged-requests): la cola es lo
  que le importa a una fraccion real de usuarios, y el promedio no la
  representa.
- RED y USE no compiten — RED dice si los CLIENTES estan sufriendo
  ahora; USE dice si un RECURSO se esta quedando sin margen antes de
  que eso pase. Un sistema bien monitoreado necesita ambos.
- Una traza distribuida vale mas que diez dashboards de latencia
  agregada cuando el problema es "por que ESTE request en particular
  tardo tanto" — son herramientas complementarias, no sustitutas.
- Esto es la base sobre la que se apoyan varios patrones anteriores:
  [SLOs y error budgets](../2-slo-error-budgets) necesitan metricas
  confiables para medirse; [chaos engineering](../1-chaos-engineering)
  necesita observabilidad real para saber si un experimento confirmo
  o refuto su hipotesis.
