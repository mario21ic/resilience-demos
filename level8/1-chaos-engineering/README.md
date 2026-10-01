# Chaos engineering / fault injection / game days

## Que es

Es la disciplina de verificar, con un experimento real y controlado,
si un mecanismo de resiliencia (un circuit breaker, un failover, un
retry) **realmente funciona** como se supone — en vez de confiar en
que funciona solo porque asi se diseño en el papel. Todos los
ejemplos de este repositorio hasta ahora asumen que el mecanismo bajo
prueba esta bien implementado; chaos engineering es la practica que
pone a prueba esa suposicion contra la realidad.

## El metodo cientifico aplicado a produccion

1. Definir un **estado estable** medible (tipicamente, la tasa de
   exito de los requests).
2. Formular una **hipotesis**: "el estado estable se mantiene incluso
   si inyectamos esta falla especifica".
3. Diseñar un **experimento** con un radio de impacto **acotado** —
   empezar chico (1% del trafico real), nunca con el 100% de una. La
   misma logica de
   [shuffle sharding](../../level3/8-sharding) y
   [cell-based architecture](../../level3/9-cell-based-arch): limitar
   cuanto puede doler si la hipotesis resulta ser falsa.
4. Observar si la hipotesis se sostiene o se refuta.
5. Si se sostiene, aumentar gradualmente el alcance para ganar mas
   confianza. Si se refuta, se encontro una debilidad real — **antes**
   de que un incidente real la expusiera sin nadie mirando ni
   preparado.

Un **game day** es la version de mayor escala de esto: un ejercicio
programado donde un equipo simula deliberadamente un incidente
significativo, para practicar tambien la RESPUESTA (no solo la
tecnica) — runbooks, comunicacion, decisiones bajo presion.

## Estructura del ejemplo

- `chaos.py`: `simulate_experiment` — inyecta una falla en una
  fraccion controlada del trafico y mide la tasa de exito resultante.
- `demo_chaos.py`: la misma progresion de radio de impacto (1%, 10%,
  50%, 100%), corrida contra un sistema donde el mecanismo de
  resiliencia funciona de verdad y otro donde esta sutilmente roto.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_chaos.py
```

Salida esperada:

```
Mecanismo funcionando: tasa de exito 100.0% en TODOS los niveles de radio
                       de impacto -> hipotesis se sostiene siempre.

Mecanismo roto: blast radius=1%  -> tasa de exito=98.8% (REFUTADA)
                blast radius=100% -> tasa de exito=0.0% (REFUTADA)
```

Con apenas 1% de trafico expuesto, ya se detecta una caida medible
(98.8% en vez de 100%) — suficiente para encontrar el problema real
con un impacto minimo.

## Puntos clave

- El punto central no es "romper cosas" — es reducir la incertidumbre
  sobre si un mecanismo de resiliencia funciona, con la menor cantidad
  de daño real posible en el proceso.
- Un experimento sin radio de impacto acotado no es chaos
  engineering, es simplemente causar un incidente — la disciplina
  completa incluye la capacidad de abortar el experimento de
  inmediato si el impacto observado supera lo esperado.
- La hipotesis tiene que ser especifica y medible ("la tasa de exito
  se mantiene sobre 99.9%"), no vaga ("el sistema deberia aguantar
  esto") — sin un numero concreto, no hay forma de decir si el
  experimento la confirmo o la refuto.
- Cada patron de este repositorio (retry, circuit breaker, bulkhead,
  failover, autoscaling...) es, en el fondo, una hipotesis sobre como
  se va a comportar el sistema ante cierto tipo de falla — chaos
  engineering es la practica de dejar de asumir y empezar a
  verificar, de forma segura y repetible.
