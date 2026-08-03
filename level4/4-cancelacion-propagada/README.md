# Cancelación propagada

## Que es

Cuando un cliente se rinde — su deadline vence, o cancela
explicitamente — esa señal deberia liberar **todo** el trabajo que se
estaba haciendo en su nombre: no solo del lado del cliente, tambien en
el servidor, y en cualquier llamada aguas abajo que ese request haya
disparado. Es el mismo concepto detras del `context.Context`
cancelable de Go, o de la deteccion de desconexion de un stream de
gRPC.

Sin esto, un servidor sigue procesando **requests zombie**: trabajo
cuyo resultado nadie va a leer nunca, porque el cliente que lo pidio
ya se fue — y, tipicamente, ya [reintento](../../level1/2-retry).

## Por que es peligroso, no solo ineficiente

El trabajo zombie no es un desperdicio aislado — compite por los
mismos recursos (threads, conexiones, CPU) que hacen falta para
procesar el trabajo REAL, incluyendo los reintentos que genero el
propio cliente que abandono. Bajo carga sostenida, esto crea un
circulo que se retroalimenta solo: mas trabajo zombie -> menos
capacidad real disponible -> mas requests exceden su deadline -> mas
trabajo zombie.

Un incidente breve en una dependencia puede, por esta via,
convertirse en una degradacion mucho mas larga que el incidente
original — el sistema no se recupera solo cuando la causa raiz se
resuelve, porque para entonces ya acumulo su propia deuda de trabajo
inutil.

## Estructura del ejemplo

- `cancellation.py`: `simulate_pileup` simula un pool fijo de 10
  workers durante un incidente temporal (una dependencia lenta por 50
  ticks), comparando que pasa con el trabajo de un cliente que se
  rindio segun si el worker se libera de inmediato o sigue
  "atendiendolo" hasta que termina solo.
- `demo_cancelacion.py`: corre ambos escenarios con la misma semilla y
  compara cola maxima, trabajo desperdiciado, y cuanto tarda el
  sistema en volver a la normalidad.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_cancelacion.py
```

Salida esperada (semilla fija; incidente de t=50 a t=100):

```
                       |  cola maxima |  worker-ticks desperdiciados |  se recupera en el tick
       SIN cancelacion |          129 |                          859 |                    1040
       CON cancelacion |           74 |                            0 |                     532
```

El incidente real duro 50 ticks. **Sin** cancelacion propagada, el
sistema tarda 1040 ticks en recuperarse — **20.8 veces** la duracion
del incidente original. **Con** cancelacion propagada, la
recuperacion es 2 veces mas rapida y no se desperdicia ni un solo
worker-tick en trabajo que nadie iba a usar.

## Puntos clave

- Cancelacion propagada es el complemento de
  [deadline propagation](../3-deadline-propagation): el deadline dice
  cuanto tiempo queda; la cancelacion es lo que efectivamente detiene
  el trabajo que ya no hace falta cuando ese tiempo se agota.
- El efecto no es lineal: un incidente corto sin cancelacion
  propagada puede generar una recuperacion desproporcionadamente
  larga, porque el trabajo zombie compite exactamente por los
  recursos que hacen falta para drenar el propio backlog que genero.
- Esto tiene que propagarse en TODA la cadena, no solo en el primer
  salto: si un servicio cancela su propio trabajo pero no le avisa a
  sus dependencias aguas abajo, el desperdicio simplemente se mueve un
  nivel mas adentro.
- En la practica, esto se implementa con primitivas del lenguaje o del
  protocolo (`context.Context` en Go, deadlines de gRPC que cancelan
  el stream del lado del servidor) — no es algo que se pueda agregar
  facil despues sobre una arquitectura que no lo penso desde el
  principio.
