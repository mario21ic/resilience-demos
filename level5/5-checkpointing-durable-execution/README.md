# Checkpointing / durable execution

## Que es

Un workflow largo (varios pasos, con esperas de minutos, horas o dias
entre uno y otro — "reservar inventario, esperar confirmacion de
pago, enviar, notificar") no puede vivir solo en la memoria de un
proceso: si el **worker** que lo esta ejecutando se cae, se reinicia,
o simplemente se reemplaza en un deploy, todo el progreso en memoria
desaparece con el.

**Durable execution** (el modelo detras de Temporal, AWS Step
Functions, Restate) resuelve esto grabando cada resultado de un paso
en un **historial durable** antes de seguir adelante. Si el worker
muere, uno nuevo puede retomar el workflow: para los pasos que ya
estan en el historial, en vez de repetir el efecto real, se usa el
resultado ya grabado (esto se llama **replay**). Solo los pasos que
todavia faltan se ejecutan de verdad.

## El requisito: determinismo

Para que el replay funcione, la funcion del workflow tiene que ser
**deterministica**: dada la misma secuencia de resultados de pasos
previos, siempre tiene que pedir los mismos pasos siguientes, en el
mismo orden. Es por eso que los motores de este tipo obligan a sacar
todo lo no-determinista (llamadas externas reales, tiempo actual,
numeros aleatorios) a "actividades" separadas, cuyo resultado se graba
y se replayea igual que cualquier otro paso — nunca se vuelve a
ejecutar la actividad en si durante un replay.

## Estructura del ejemplo

- `durable.py`: `History` (el registro durable), `World` (los efectos
  reales, con contadores para detectar duplicados), y
  `run_order_workflow` — la funcion del workflow, que decide replay
  vs ejecucion real segun lo que ya haya en el historial.
- `demo_durable.py`: tres partes.
  1. Sin checkpointing: el reinicio repite todo desde cero.
  2. Con checkpointing: se retoma exactamente donde quedo.
  3. El argumento de capacidad: cuantos workflows en vuelo puede
     sostener un pool fijo de workers, con y sin esta propiedad.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_durable.py
```

Salida esperada (el worker muere tras 2 pasos reales, de 4 totales):

```
Parte 1 (sin checkpointing): reservas=2, cobros=2, envios=1, notificaciones=1
                              -> doble cobro, doble reserva

Parte 2 (con checkpointing):  reservas=1, cobros=1, envios=1, notificaciones=1
                              -> cada efecto ocurrio exactamente una vez

Parte 3: pool de 10 workers, workflow que vive 24hs pero solo trabaja 50s reales
  sin checkpointing: maximo 10 workflows en curso a la vez
  con checkpointing: hasta 17.280 workflows en curso a la vez
```

## Puntos clave

- El historial no es un log de auditoria opcional — ES el estado del
  workflow. Sin el, no hay forma de saber que ya paso al retomarlo.
- El replay es barato porque no ejecuta efectos reales: un workflow
  con cientos de pasos completados se puede reconstruir en
  milisegundos, sin volver a cobrar, reservar, ni enviar nada.
- La consecuencia menos obvia (Parte 3) es de capacidad: un workflow
  "esperando" no necesita ningun worker corriendo — solo hace falta
  uno en los breves momentos en que ejecuta un paso real. Esto es lo
  que permite sostener millones de workflows de larga duracion con
  una flota de workers modesta.
- Esto se apoya en las mismas ideas que
  [consumidor idempotente](../3-consumidor-idempotente-dedup) (no
  repetir un efecto ya aplicado) y
  [event sourcing](../8-event-sourcing) (el estado se reconstruye
  desde un log de eventos, no se guarda directamente) — durable
  execution es esencialmente event sourcing aplicado al **control de
  flujo** de un programa, no solo a sus datos.
