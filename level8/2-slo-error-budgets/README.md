# SLO + error budgets

## Que es

Un **SLO** (Service Level Objective) es un objetivo de confiabilidad
— "99.9% de los requests exitosos en una ventana de 30 dias". Su
complemento es el **error budget**: la cantidad de falla que ese SLO
permite, expresada como una cantidad **concreta y gastable** (minutos
de downtime, requests fallidos permitidos) — no solo un porcentaje
abstracto en un dashboard.

Convertir la confiabilidad en un presupuesto gastable es lo que
habilita decisiones explicitas: si queda presupuesto, tiene sentido
asumir mas riesgo (desplegar mas seguido, experimentar); si ya se
gasto, toca frenar cambios riesgosos y priorizar estabilidad. El SLO
no es un piso que hay que superar siempre a cualquier costo — es un
objetivo que, una vez cumplido, libera margen para otras prioridades.
Es, literalmente, el marco que decide cuanto de todo lo demas en este
repositorio (redundancia, multi-region, chaos testing) vale la pena
comprar.

## El costo de cada nueve adicional

Cada nueve extra de SLO (99% -> 99.9% -> 99.99%...) divide por 10 el
presupuesto de downtime disponible — y, en la practica, el costo de
ingenieria para conseguirlo crece todavia mas rapido que eso. Elegir
el SLO correcto (no el mas alto posible) es en si mismo parte del
trabajo: cuanta confiabilidad necesita realmente el negocio, no
cuanta se podria conseguir en teoria con suficiente inversion.

## Burn rate: la velocidad importa tanto como el nivel

El **burn rate** mide a que velocidad se esta consumiendo el
presupuesto ahora mismo, en relacion al ritmo "sostenible" (el que lo
agotaria justo al final del periodo). Un burn rate alto amerita
respuesta inmediata aunque todavia quede presupuesto en el papel,
porque a ese ritmo no va a durar — es la base de las alertas
modernas de SRE (el enfoque "multi-window, multi-burn-rate" de
Google), que reaccionan a la tendencia, no solo al nivel absoluto.

## Estructura del ejemplo

- `error_budgets.py`: `allowed_downtime_minutes`,
  `error_budget_requests`, `time_to_exhaust_days`.
- `demo_error_budgets.py`: tres partes — el presupuesto como cantidad
  concreta, el costo geometrico de cada nueve adicional, y el burn
  rate como señal de cuando actuar.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_error_budgets.py
```

Salida esperada:

```
Parte 1: SLO=99.9%, presupuesto del mes = 300,000 requests fallidos
         un incidente de 50,000 fallos consume 16.7% del presupuesto

Parte 2: 99%    -> 432.00 min/mes permitidos
         99.9%  ->  43.20 min/mes
         99.99% ->   4.32 min/mes
         99.999%->   25.9 seg/mes

Parte 3: burn rate 1.0x  -> se agota justo en 30 dias (sostenible)
         burn rate 10.0x -> se agota en 3 dias (atencion)
         burn rate 50.0x -> se agota en 14.4 horas (URGENTE)
```

## Puntos clave

- El error budget convierte una discusion subjetiva ("¿esto es
  suficientemente confiable?") en una decision con numeros: cuanto
  presupuesto queda, a que ritmo se esta gastando, cuanto permite
  todavia.
- Un presupuesto agotado no es necesariamente una emergencia tecnica
  — es una señal organizacional: dejar de priorizar features nuevas y
  priorizar trabajo de confiabilidad hasta recuperar margen.
- El SLO tiene que medir algo que le importe de verdad al usuario
  (exito de un request, no "el servidor esta prendido") — un SLO mal
  elegido puede estar perfecto en el dashboard mientras los usuarios
  reales tienen una mala experiencia.
- Cada patron de este repositorio — redundancia, multi-region,
  circuit breakers, chaos engineering — tiene un costo. El error
  budget es el marco que conecta ese costo con un objetivo de negocio
  concreto, en vez de perseguir "mas resiliencia" como un fin en si
  mismo.
