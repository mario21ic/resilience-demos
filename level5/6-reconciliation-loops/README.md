# Reconciliation loops

## Que es

Es el modelo de control detras de Kubernetes: en vez de ejecutar una
accion una vez y confiar en que el resultado se mantenga, un
controlador compara **continuamente** el estado deseado (la spec:
"quiero 3 replicas") contra el estado real observado, y aplica la
diferencia — una y otra vez, para siempre. **Convergencia continua**
en lugar de **correccion puntual**.

## Por que "hacerlo una vez" no alcanza

Un script imperativo que crea 3 replicas y termina no tiene forma de
enterarse si, mas tarde, una de ellas desaparece — un nodo que muere,
alguien que borra un pod a mano, cualquier interferencia externa. El
sistema queda silenciosamente por debajo de lo deseado, y **nada lo
corrige**, porque el codigo que sabia como corregirlo ya termino de
ejecutarse hace rato.

## Dos propiedades que hacen esto robusto

- **Por nivel, no por evento**: el loop no reacciona a "que paso" —
  mira "como esta todo AHORA" contra "como deberia estar", en cada
  pasada. Esto lo hace inmune a perder eventos: no importa si un
  aviso de "se borro un pod" nunca llego, porque el loop no depende
  de haberlo recibido — la proxima vez que compare la realidad, va a
  notar la discrepancia igual.
- **Idempotente**: reconciliar un estado que ya coincide con lo
  deseado no hace nada. Es seguro correr el loop todo el tiempo, sin
  condiciones especiales para "solo cuando algo cambio".

## Estructura del ejemplo

- `reconciliation.py`: `simulate_imperative` (crea una vez y no vuelve
  a mirar), `simulate_reconciliation` (compara y corrige en cada
  tick), `simulate_edge_triggered` (reacciona a eventos, que a veces
  se pierden).
- `demo_reconciliation.py`: dos partes.
  1. Imperativo vs reconciliacion continua, con interferencia externa
     aleatoria en cada tick.
  2. Por evento vs por nivel, cuando una fraccion de los eventos que
     dispararian una correccion se pierde en el camino.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_reconciliation.py
```

Salida esperada (semilla fija; se desean 3 replicas, 10% de
probabilidad de perder una por tick):

```
Parte 1:
  imperativo:      promedio 0.14/3, termina en 0
  reconciliacion:  promedio 3.00/3, termina en 3

Parte 2 (30% de los eventos se pierden):
  por evento:  promedio 0.62/3, termina en 0
  por nivel:   promedio 3.00/3, termina en 3
```

En ambas partes, cualquier enfoque que dependa de "actuar una vez" o
de "enterarse de cada evento" se degrada monotonamente hasta cero. La
reconciliacion por nivel se mantiene exactamente en el objetivo todo
el tiempo, sin excepcion.

## Puntos clave

- El costo de reconciliar continuamente es bajo cuando el loop es
  idempotente: la inmensa mayoria de las pasadas no encuentran
  diferencia y no hacen nada — el costo aparece solo cuando realmente
  hace falta corregir algo.
- Este modelo asume que se puede **observar el estado real** de forma
  confiable (listar los pods que existen de verdad) — la
  reconciliacion es tan buena como la fuente de verdad contra la que
  compara.
- Level-triggered no significa "ignorar eventos" — los sistemas reales
  (Kubernetes incluido) usan eventos como una señal para reconciliar
  MAS SEGUIDO cuando algo cambio, pero nunca confian en el evento en
  si como la unica fuente de la correccion — siempre vuelven a mirar
  el estado real antes de actuar.
- Esta es la misma idea que
  [anti-entropy y read repair](../7-anti-entropy-read-repair-merkle):
  en vez de tratar de que cada operacion individual sea perfecta,
  se acepta que van a pasar cosas, y se invierte en un mecanismo que
  encuentre y corrija divergencias de forma continua y automatica.
