# Failover — automático o manual, disparado por health checks

## Que es

**Failover** es el proceso de promover un standby a primario cuando
el primario actual se considera caido. La pregunta de este ejemplo no
es "hacer failover o no" — es **como se dispara** (health checks con
un umbral, no un solo check fallido) y **quien lo ejecuta**
(automatico o manual), y por que la respuesta correcta no es "siempre
automatico, es mas rapido": el enemigo de todo esto es el
**split-brain**.

## El problema de fondo: un health check no puede saber la verdad

Un health checker solo sabe una cosa con certeza: "pude o no pude
contactar al primario en este check". **No puede distinguir entre
"esta muerto" y "esta vivo pero inalcanzable desde aca"** — una
particion de red se ve exactamente igual que una caida real desde el
punto de vista de quien esta chequeando.

Si se promueve un standby creyendo que el primario murio, y en
realidad solo estaba particionado, quedan **dos nodos que se creen
primario al mismo tiempo**: split-brain. Ambos aceptan escrituras de
sus propios clientes, sin saber del otro. Cuando la particion se
cura, hay que reconciliar datos que divergieron — y eso, en el mejor
de los casos, requiere decidir que escritura descartar.

## Automatico vs manual: velocidad contra prudencia

- **Automatico**: dispara apenas el health checker cruza el umbral de
  fallas consecutivas. Rapido — restaura servicio en segundos ante una
  caida real. Pero no tiene forma de saber si esta reaccionando a una
  caida real o a una particion, asi que reacciona igual en ambos
  casos.
- **Manual**: exige confirmacion humana antes de promover. Mas lento
  ante una caida real (el servicio queda caido mas tiempo esperando a
  la persona), pero le da tiempo a que una particion transitoria se
  resuelva sola antes de actuar — a veces evita un failover
  innecesario simplemente por no haber llegado a tiempo a dispararlo.

Ninguno de los dos resuelve el problema de fondo: manual solo lo hace
**mas lento**, reduciendo la ventana en la que un falso positivo se
alcanza a ejecutar, pero si la particion dura lo suficiente, tambien
termina disparando.

## La defensa estructural: fencing por generacion

El fencing no evita que el split-brain ocurra — evita que **haga
daño**. Cada vez que se promueve un primario nuevo, recibe una
generacion (epoch/term) mayor que la anterior, registrada de
inmediato en el recurso compartido (storage, servicio downstream).
Ese recurso solo acepta escrituras de la generacion mas alta que haya
visto. El primario viejo, que nunca se entero de que fue reemplazado,
sigue mandando escrituras con su generacion vieja — y esas
escrituras se **rechazan explicitamente** en vez de aplicarse en
silencio.

Es la misma idea detras de los *fencing tokens* de los locks
distribuidos, y de los *terms* de Raft: la ambiguedad de "quien es el
primario de verdad" se resuelve dejando que el recurso compartido
arbitre por numero de generacion, no confiando en que cada nodo sepa
por si solo si sigue siendo el primario.

## Estructura del ejemplo

- `health_check.py`: `HealthChecker` (umbral de fallas consecutivas),
  `AutomaticFailover` y `ManualFailover` (mismo trigger, distinta
  velocidad de reaccion).
- `fencing.py`: `FencedStorage`, que solo acepta escrituras de la
  generacion mas alta que ha visto; `FencedError` cuando una
  escritura vieja intenta colarse.
- `demo_failover.py`: tres partes sobre la misma linea de tiempo de
  health checks.
  1. Falla real: compara cuanto tarda cada estrategia en restaurar
     servicio.
  2. Particion de red: el health checker ve exactamente la misma
     señal que en una falla real. El failover automatico promueve un
     standby mientras el primario viejo sigue vivo y sirviendo —
     split-brain real, con una escritura legitima perdida en
     silencio.
  3. La misma particion, con fencing: el primario viejo sigue
     intentando escribir, pero sus escrituras se rechazan — el saldo
     final queda correcto.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_failover.py
```

Salida esperada (resumen):

```
Parte 1 (falla real):
  automatico: disparado en t=7, promocion completa en t=9
  manual: disparado en t=12, promocion completa en t=14
  -> automatico restaura servicio 5 ticks antes que manual

Parte 2 (particion, SIN fencing):
  t=10: primario NUEVO procesa un deposito -> saldo=130
  t=11: primario VIEJO procesa un retiro -> saldo=70
  saldo final en el storage compartido: 70   <- INCORRECTO, se perdio el deposito legitimo

Parte 3 (misma particion, CON fencing):
  t=11: primario VIEJO (generacion 1) intenta procesar un retiro...
    -> RECHAZADO: escritura rechazada: generacion 1 es vieja (la generacion actual es 2)
  saldo final: 130   <- correcto
```

En la Parte 2, el saldo final (70) es **el resultado equivocado**: el
deposito del primario vigente quedo pisado por una escritura de un
nodo que ya no deberia poder escribir, sin ningun error visible. En
la Parte 3, con la misma secuencia de eventos, el fencing rechaza esa
escritura y el saldo final (130) es el correcto.

## Puntos clave

- Un health check mide alcanzabilidad, no vida — nunca hay que
  tratarlo como una fuente de verdad absoluta sobre si un nodo esta
  realmente caido.
- Failover automatico y manual son un tradeoff de velocidad vs
  prudencia, no una solucion al split-brain — la Parte 2 muestra que
  incluso "tener suerte" con el timing del manual no es una defensa
  real.
- Fencing es lo que permite tener automatico Y seguro al mismo
  tiempo: la velocidad de reaccion no cambia, pero el daño potencial
  de una promocion equivocada se vuelve un error visible en vez de
  una corrupcion silenciosa.
- Esto se combina con [redundancia N+1/N+2](../redundancia-n1-n2):
  la topologia decide CUANTOS standbys hay disponibles; el failover
  decide COMO y CUANDO promover a uno; el fencing decide que hacer
  para que promover al equivocado no sea catastrofico.
