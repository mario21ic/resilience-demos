# Constant work pattern

## Que es

Es un patron documentado por AWS: en vez de que un sistema haga
**poco** trabajo en el dia a dia y **mucho** trabajo durante una
crisis (un sistema **bimodal**, con dos comportamientos muy
distintos segun la situacion), se lo diseña para hacer siempre la
**misma** cantidad de trabajo, haya o no haya cambios reales que
procesar.

El ejemplo clasico: en vez de propagar solo los cambios de DNS que
ocurrieron (un sistema "delta"), Route 53 reenvia periodicamente el
estado **completo** de todos los registros, todo el tiempo. Un
incidente que genera muchos cambios de golpe no le pide al sistema
hacer algo nuevo — ya estaba haciendo ese volumen de trabajo,
siempre, sin excepcion.

## Dos problemas que la bimodalidad genera

1. **Capacidad**: un sistema delta dimensionado para el volumen
   normal se desborda ante una rafaga real (justo cuando mas
   importa). Dimensionarlo para el peor caso evita eso, pero
   desperdicia casi toda esa capacidad el resto del tiempo — 0.4% de
   utilizacion en este ejemplo.
2. **Confianza**: el "modo crisis" de un sistema bimodal es,
   precisamente por ser raro, el camino de codigo **menos probado**
   — exactamente el que mas necesita funcionar cuando llega el
   momento. Es la misma logica por la que un backup nunca probado no
   es una garantia de nada (ver
   [DR con RTO/RPO](../../level8/4-dr-rto-rpo)).

Trabajo constante resuelve ambos a la vez: el volumen de trabajo del
"modo crisis" es literalmente el mismo que el del modo normal, asi
que esta tan probado como cualquier ciclo comun.

## Estructura del ejemplo

- `constant_work.py`: `simulate_delta_recovery` (cuantos ciclos tarda
  un sistema delta en absorber una rafaga real) y
  `constant_work_cycles_to_recover` (por que un sistema de trabajo
  constante no genera backlog en absoluto, mientras la rafaga quepa
  dentro de su volumen habitual).
- `demo_constant_work.py`: compara ambos sistemas ante la misma
  rafaga de 500 cambios reales.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_constant_work.py
```

Salida esperada:

```
Sistema delta (dimensionado para 5 cambios/ciclo): tarda 100 ciclos en
                                                    absorber la rafaga.
  si se dimensiona para el peor caso (500/ciclo): 0.4% de utilizacion diaria.

Sistema de trabajo constante (siempre 1000 registros/ciclo):
  ciclos de backlog generados por la rafaga: 0
```

## Puntos clave

- El costo de trabajo constante es real y deliberado: se paga por
  hacer trabajo "de mas" la mayor parte del tiempo, a cambio de
  eliminar el peor escenario posible (que la capacidad de crisis no
  alcance, o ni siquiera funcione, justo cuando se la necesita).
- No todo sistema puede volverse de trabajo constante — tiene sentido
  cuando el volumen del estado completo es acotado y manejable (mil
  registros de DNS, no mil millones). Para datasets enormes, la
  estrategia delta con buena capacidad de rafaga sigue siendo
  necesaria.
- Esto es la misma logica que
  [reconciliation loops](../../level5/6-reconciliation-loops): en vez
  de reaccionar puntualmente a cada cambio, se corre el mismo proceso
  completo una y otra vez — la diferencia es que aca el enfasis esta
  en la CAPACIDAD constante, no en la convergencia hacia un estado
  deseado.
- Un sistema bimodal tambien es mas dificil de operar: cualquier
  alarma o dashboard calibrado para el modo normal va a verse "raro"
  durante una crisis, generando ruido justo cuando la señal real
  importa mas. Un sistema de trabajo constante se ve igual siempre —
  las anomalias reales resaltan mas, no menos.
