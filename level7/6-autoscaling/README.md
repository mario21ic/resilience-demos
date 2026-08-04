# Autoscaling — reactivo, predictivo, y el límite de fondo

## Que es

Agregar o quitar capacidad segun la demanda, en vez de provisionar
siempre para el peor caso posible. Dos estrategias:

- **Reactivo**: mide la demanda real y agrega capacidad cuando hace
  falta. Tiene un retraso inherente — tiempo de **deteccion** (cada
  cuanto se revisan las metricas) mas tiempo de
  **aprovisionamiento** (cuanto tarda una instancia nueva en estar
  lista) — y durante ese retraso, la demanda que ya llego y no se
  puede atender se pierde.
- **Predictivo**: usa patrones conocidos (la hora pico de todos los
  dias, un evento programado) para escalar ANTES de que la demanda
  suba, evitando el retraso — pero solo sirve para lo que se puede
  anticipar.

## El limite de fondo: nunca mas rapido que el fallo

El autoscaling nunca puede reaccionar mas rapido que su propio tiempo
de deteccion + aprovisionamiento. Si un incidente (una rafaga de
trafico viral, una [tormenta de reintentos](../../level1/6-retry-budget))
crece mas rapido que eso, el autoscaling **solo** no alcanza para
evitar la perdida — no importa que tan bien configurado este. Hacen
falta otros mecanismos ([load shedding](../../level2/5-load-shedding),
[circuit breakers](../../level2/1-circuit-breaker), capacidad
[pre-aprovisionada](../../level3/10-multi-az)) para sobrevivir la
ventana antes de que la capacidad nueva este lista.

## Estructura del ejemplo

- `autoscaling.py`: `simulate_reactive`, `simulate_predictive` y
  `exponential_demand` (para modelar un incidente que crece
  exponencialmente).
- `demo_autoscaling.py`: tres partes.
  1. Cuanta demanda se pierde durante el retraso de un autoscaler
     reactivo ante un pico subito.
  2. Predictivo vs reactivo, para el mismo pico, sabiendo de antemano
     cuando va a ocurrir.
  3. Cuanto se pierde segun que tan rapido crece el incidente en
     relacion al tiempo de reaccion del autoscaler.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_autoscaling.py
```

Salida esperada:

```
Parte 1: demanda perdida durante el retraso reactivo: 4200

Parte 2: reactivo: 4200 perdidos
         predictivo (sabe del pico de antemano): 0 perdidos

Parte 3 (autoscaler con ~8 ticks de reaccion):
  incidente duplica cada  2 ticks: 82.7% de demanda perdida
  incidente duplica cada  8 ticks: 23.2% de demanda perdida
  incidente duplica cada 30 ticks:  0.0% de demanda perdida
```

## Puntos clave

- El tiempo de aprovisionamiento no es solo "cuanto tarda la API en
  crear la instancia" — incluye boot, inicializacion de la
  aplicacion, y calentamiento de caches. Subestimarlo es la forma mas
  comun de que un autoscaler "bien configurado" siga sin alcanzar.
- Predictivo y reactivo no son excluyentes: un sistema real suele
  combinar ambos — predictivo para los patrones conocidos, reactivo
  como red de seguridad para lo que el modelo no anticipo.
- La Parte 3 es la razon por la que
  [static stability](../../level3/10-multi-az) recomienda
  pre-aprovisionar capacidad para el escenario de falla mas probable,
  en vez de confiar en que el autoscaling reaccione a tiempo — para
  el peor caso (perder una zona entera de golpe), simplemente no hay
  tiempo de reaccion suficiente.
- Autoscaling reduce COSTO (no pagar capacidad ociosa la mayor parte
  del tiempo); no reemplaza a los mecanismos que protegen al sistema
  MIENTRAS la capacidad nueva todavia no esta lista.
