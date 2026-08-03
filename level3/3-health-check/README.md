# Health checks — liveness / readiness / startup

## Que es

Los orquestadores y load balancers deciden que hacer con una instancia
en base a health checks, pero no todos los checks significan lo
mismo ni deberian disparar la misma accion:

- **Liveness** ("¿esta vivo el proceso?"): si falla, el orquestador
  **mata y reinicia** la instancia. Tiene que ser barato y
  **superficial** — confirmar que el proceso responde, nunca revisar
  dependencias externas. Reiniciar el proceso no arregla una base de
  datos caida; solo agrega un reinicio encima de una falla que sigue
  ahi.
- **Readiness** ("¿esta lista esta instancia para recibir trafico
  AHORA?"): si falla, se la **saca de la rotacion** del load
  balancer, sin matarla ni reiniciarla. Aca si tiene sentido revisar
  dependencias — pero solo las que son **realmente esenciales**.
- **Startup**: una version mas permisiva de liveness, usada solo
  mientras la instancia arranca (init lento, precarga de cache), para
  no matarla por "no responde todavia" cuando en realidad solo esta
  iniciando.

## El enemigo: un chequeo profundo mal ubicado

Un chequeo **profundo** (revisa dependencias externas, no solo el
proceso) no es malo en si mismo — es exactamente lo que necesita la
readiness para saber si de verdad puede servir. El problema aparece
en dos formas concretas, y este ejemplo demuestra ambas:

1. **Chequeo profundo en el probe equivocado**: ponerlo en la
   LIVENESS en vez de en la READINESS. Un blip transitorio de una
   dependencia compartida tumba la liveness de TODA la flota al mismo
   tiempo -> se reinician todas juntas. El reinicio (reconectar,
   precalentar cache) tarda mucho mas que el blip original, y en
   sistemas reales una oleada sincronizada de reconexiones puede
   incluso demorar la recuperacion de la dependencia que se estaba
   revisando.
2. **Chequeo profundo sobre la dependencia equivocada**: incluir en
   la readiness algo que **no es esencial** para servir la mayoria
   del trafico. Una falla parcial y menor termina tumbando el 100% de
   la capacidad por algo que ni siquiera hacia falta.

## Estructura del ejemplo

- `health_probes.py`: `simulate_liveness_scope` (compara chequear la
  DB en liveness vs en readiness) y `simulate_readiness_scope`
  (compara incluir o no una dependencia no esencial en la readiness).
  Simulaciones puras, tick a tick, sin red ni threads.
- `demo_health_checks.py`: dos partes, cada una contrastando el mal
  diseño contra el buen diseño sobre la misma falla simulada.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_health_checks.py
```

Salida esperada:

```
Parte 1 (blip de la DB de 5 ticks, t=5 a t=9):
  DB revisada en LIVENESS (mal):    caida 0% -> 11/25 ticks (se reinicia TODA la flota)
  DB revisada en READINESS (bien):  caida 0% ->  5/25 ticks (exactamente el blip real)

Parte 2 (blip de un servicio NO esencial, t=5 a t=9):
  readiness exige tambien 'recomendaciones' sano (mal): 5/20 ticks caido
  readiness solo exige la DB principal sana (bien):     0/20 ticks caido
```

En la Parte 1, el chequeo en el lugar equivocado **mas que duplica**
el tiempo de caida (11 vs 5 ticks): el blip real dura 5 ticks, pero
hay que sumarle el tiempo que tarda toda la flota en terminar de
reiniciarse. En la Parte 2, incluir una dependencia no esencial en la
readiness convierte una falla que no debería afectar a nadie en un
apagon total (5 ticks caido vs 0).

## Puntos clave

- Liveness responde "¿reinicio esto?" — la respuesta casi siempre
  deberia depender solo del proceso en si, nunca de una dependencia
  externa que un reinicio no puede arreglar.
- Readiness responde "¿le mando trafico a esto ahora?" — aca si vale
  revisar dependencias, pero la pregunta clave es "¿esta dependencia
  es realmente necesaria para servir?", no "¿esta dependencia esta
  sana?".
- Si una dependencia no es esencial, la respuesta correcta no es
  sacarla de la readiness y listo — es manejar su falla con un
  [fallback](../../level1/8-fallback) dentro del request, para que la
  degradacion sea de esa funcionalidad puntual, no de toda la
  instancia.
- Este patron es la version "dentro de una sola instancia" del
  problema de [failover](../2-failover): un chequeo que no puede
  distinguir "un problema real y aislado" de "hay que tirar todo
  abajo" convierte fallas parciales en fallas totales — la cascada no
  viene de la falla original, viene de como se reacciona a ella.
