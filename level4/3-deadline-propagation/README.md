# Deadline propagation

## Que es

Un cliente que llama a un servicio esta dispuesto a esperar, como
mucho, un tiempo total (su **deadline**). Si ese request atraviesa
varias capas antes de responder (un gateway, un par de servicios
intermedios, una consulta final), cada capa deberia saber **cuanto le
queda realmente** al cliente original — no aplicar su propio timeout
fijo, elegido a mano y desconectado de ese presupuesto.

Deadline propagation es exactamente eso: pasar el presupuesto de
latencia **restante** (deadline original menos lo ya gastado) hacia
adelante en cada llamada de la cadena. Es la idea detras del
`context.Context` con deadline de Go, y de los deadlines de gRPC.

## El problema sin propagacion

Sin propagacion, cada capa configura su propio timeout local para la
llamada siguiente (un valor tipico, elegido una vez y olvidado — "80ms
deberia alcanzar"). El problema: ese numero no sabe nada del cliente
original. Si el request ya viene con jitter acumulado de las capas
anteriores, la SUMA de "cada timeout local individualmente
razonable" puede superar tranquilamente lo que el cliente esperaba —
aunque cada capa, vista de forma aislada, haya cumplido su propio
limite.

## La idea: pasar el presupuesto, no un timeout fijo

Con propagacion, cada capa calcula:

```
remaining = deadline_original - tiempo_ya_gastado
```

y le pasa **ese** numero (no un valor fijo) a la siguiente llamada.
Esto tiene dos consecuencias:

1. La suma de tiempos nunca puede superar el deadline original — es
   una garantia estructural, no una esperanza.
2. Si en algun punto ya no queda presupuesto suficiente para que la
   siguiente llamada tenga sentido, esa capa puede **responder de
   inmediato** (un fallback, un error explicito) en vez de arrancar un
   trabajo que sabe de antemano que no va a poder terminar a tiempo.

## Estructura del ejemplo

- `deadlines.py`: `call_chain_without_propagation` (timeout fijo por
  capa) y `call_chain_with_propagation` (presupuesto restante
  calculado en cada capa, con umbral minimo para decidir si vale la
  pena intentar el ultimo salto).
- `demo_deadline_propagation.py`: corre 50.000 requests simulados por
  ambas estrategias y compara latencia promedio, cuantos exceden el
  deadline original, y cuantos llegan siquiera a intentar la llamada
  final.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_deadline_propagation.py
```

Salida esperada (semilla fija):

```
          estrategia |  latencia promedio |  excede el deadline |  llamada final intentada
     sin propagacion |             85.1ms |              21.2% |                  100.0%
     con propagacion |             56.9ms |               0.0% |                   31.8%
```

Sin propagacion, **1 de cada 5 requests** termina tardando mas de lo
que el cliente estaba dispuesto a esperar. Con propagacion, eso nunca
pasa — y ademas casi un tercio de los requests se resuelven mas rapido
todavia, porque una capa intermedia se da cuenta a tiempo de que ya no
vale la pena intentar el ultimo salto.

## Puntos clave

- El deadline es del **cliente original**, no de cada capa — cada
  timeout local deberia ser una fraccion de ESE presupuesto, no un
  numero independiente.
- Propagar el deadline no solo evita exceder el limite: tambien
  habilita decisiones de **fail fast** que serian imposibles sin esa
  informacion (¿tiene sentido intentar esto con lo que me queda?).
- Esto se complementa directo con
  [level1/8-fallback](../../level1/8-fallback): cuando el presupuesto
  no alcanza, la respuesta correcta no es un error crudo — es
  degradar con lo que ya se tiene, igual de rapido.
- Sin cancelacion propagada (ver
  [4-cancelacion-propagada](../4-cancelacion-propagada)), el trabajo
  que un timeout local corta del lado del CLIENTE puede seguir
  corriendo del lado del SERVIDOR, desperdiciado — deadline
  propagation dice cuanto tiempo queda; cancelacion propagada es lo
  que efectivamente detiene el trabajo que ya no hace falta.
